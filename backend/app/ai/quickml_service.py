"""backend/app/ai/quickml_service.py

Application layer service orchestrating the complete CaseClock AI workflow:
conversation context assembly, intent extraction, confidence validation,
graph service dispatching, synthesis prompt rendering, QuickML client invocation,
and ChatResponse formatting.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from backend.app.ai.exceptions import MissingEntityError
from backend.app.ai.intent_dispatcher import IntentDispatcher, IntentName

from backend.app.ai.intent_extractor import IntentExtractor
from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationContext,
    Intent,
    LLMRequest,
    LLMResponse,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import GraphService
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.network_service import NetworkService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.core.graph.services.similarity_service import SimilarityService

logger = logging.getLogger(__name__)

# Default minimum confidence threshold for intent extraction validation
DEFAULT_MIN_CONFIDENCE_THRESHOLD: float = 0.60

MISSING_ENTITY_CLARIFICATIONS: dict[str, dict[str, str]] = {
    "GET_SIMILAR_CASES": {
        "case_id": "I need a reference case to find similar cases.\nPlease specify a case identifier, for example:\n\n    Show similar cases to FIR/BEL/0064",
    },
    "GET_CASE": {
        "case_id": "I need a case identifier to show case details.\nPlease specify a case identifier, for example:\n\n    Show case FIR/BEL/0064",
    },
    "GET_CASE_DETAILS": {
        "case_id": "I need a case identifier to show full case details.\nPlease specify a case identifier, for example:\n\n    Show case details for FIR/BEL/0064",
    },
    "GET_NETWORK": {
        "case_id": "I need a case identifier to build the network graph.\nPlease specify a case identifier, for example:\n\n    Show network for FIR/BEL/0064",
        "officer_id": "I need a case or officer identifier to build the network graph.\nPlease specify a case identifier, for example:\n\n    Show network for FIR/BEL/0064",
    },
    "GET_CLOCK": {
        "case_id": "I need a case identifier to display statutory clocks.\nPlease specify a case identifier, for example:\n\n    Show investigation clock for FIR/BEL/0064",
    },
    "GET_DEPENDENCIES": {
        "case_id": "I need a case identifier to show pending dependencies.\nPlease specify a case identifier, for example:\n\n    Show dependency chain for FIR/BEL/0064",
    },
    "GET_CO_ACCUSED": {
        "person_id": "I need a person identifier to find co-accused individuals.\nPlease specify a person identifier, for example:\n\n    Show co-accused for Person P-101",
    },
    "GET_OFFENDER_PROFILE": {
        "person_id": "I need a person identifier to show an offender profile.\nPlease specify a person identifier, for example:\n\n    Show profile for Person P-101",
    },
}


class QuickMLService:

    """Application layer orchestrator for the CaseClock AI pipeline."""

    def __init__(
        self,
        client: QuickMLClient,
        prompt_manager: PromptManager,
        intent_extractor: IntentExtractor | None = None,
        intent_dispatcher: IntentDispatcher | None = None,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE_THRESHOLD,
    ) -> None:
        """Initialize QuickMLService with injected dependencies.

        Args:
            client: Infrastructure client for QuickML API execution.
            prompt_manager: Manager for prompt template retrieval and rendering.
            intent_extractor: Extractor for NLU intent parsing (lazily constructed if None).
            intent_dispatcher: Dispatcher for deterministic graph services (lazily constructed if None).
            min_confidence_threshold: Minimum confidence score required before dispatching graph intent.
        """
        self._client = client
        self._prompt_manager = prompt_manager
        self._min_confidence_threshold = min_confidence_threshold

        if intent_extractor is not None:
            self._intent_extractor = intent_extractor
        else:
            self._intent_extractor = IntentExtractor(
                client=client,
                prompt_manager=prompt_manager,
            )

        if intent_dispatcher is not None:
            self._intent_dispatcher = intent_dispatcher
        else:
            repo = GraphRepository()
            self._intent_dispatcher = IntentDispatcher(
                graph_service=GraphService(repo),
                hotspot_service=HotspotService(repo),
                network_service=NetworkService(repo),
                offender_service=OffenderService(repo),
                similarity_service=SimilarityService(repo),
            )

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Processes an incoming ChatRequest and returns a formatted ChatResponse.

        Target Pipeline:
            ChatRequest
                ↓
            ConversationContext
                ↓
            IntentExtractor
                ↓
            Intent + Confidence Threshold Validation
                ↓
            IntentDispatcher (if graph intent; bypassed for GENERAL_CHAT / UNKNOWN)
                ↓
            Deterministic Graph Result
                ↓
            PromptManager.render(PromptType.SYNTHESIS, user_query, intent_name, confidence, entities, graph_result)
                ↓
            QuickMLClient.generate()
                ↓
            ChatResponse

        Args:
            request: Presentation layer ChatRequest payload.

        Returns:
            Presentation layer ChatResponse payload populated with message,
            conversation_id, intent, entities, data, and metadata.

        Raises:
            QuickMLError: If QuickML client execution fails.
            PromptError: If system or synthesis prompt retrieval fails.
            IntentExtractionError: If intent extraction or schema validation fails.
            ToolExecutionError: If deterministic graph tool execution fails.
            AIError: For generic AI subsystem failures.
        """
        context = self._build_context(request)

        # Step 1: Extract intent from user query using IntentExtractor
        intent = self._intent_extractor.extract(request.message)

        # Step 2: Validate confidence threshold (safely downgrade low-confidence intent to UNKNOWN)
        if (
            intent.confidence is not None
            and intent.confidence < self._min_confidence_threshold
        ):
            logger.warning(
                "Intent '%s' confidence (%.2f) below threshold (%.2f); downgrading to UNKNOWN.",
                intent.name,
                intent.confidence,
                self._min_confidence_threshold,
            )
            intent = Intent(
                name=IntentName.UNKNOWN.value,
                confidence=intent.confidence,
                entities=intent.entities,
            )

        # Step 3: GENERAL_CHAT / UNKNOWN intent bypass
        if intent.name in (IntentName.GENERAL_CHAT.value, IntentName.UNKNOWN.value):
            logger.info("Executing general chat bypass flow for intent=%s", intent.name)
            messages = self._build_messages(context, request.message)
            llm_request = self._build_llm_request(messages)
            llm_response = self._client.generate(llm_request)
            return self._build_chat_response(
                context=context,
                llm_response=llm_response,
                intent=intent,
                data=None,
            )

        # Step 4: Dispatch graph intent to deterministic services
        logger.info("Dispatching intent=%s to deterministic graph services", intent.name)
        try:
            graph_data = self._intent_dispatcher.dispatch(intent)
        except MissingEntityError as e:
            logger.info("Missing required entity '%s' for intent '%s'", e.entity_type, e.intent_name)
            clarification_msg = self._build_missing_entity_clarification(e.intent_name, e.entity_type)
            return self._build_chat_response(
                context=context,
                llm_response=LLMResponse(content=clarification_msg),
                intent=intent,
                data=None,
            )

        # Preprocess / truncate large collections to keep prompt size within gateway limits
        truncated_graph_data = self._truncate_graph_data(graph_data)


        # Step 5: Render synthesis prompt using PromptManager with rich context
        entities_formatted = [
            {"type": e.type, "value": e.value} for e in intent.entities
        ]
        graph_data_str = json.dumps(truncated_graph_data, indent=2, default=str)

        print("=" * 50)
        print("GRAPH RESULT SIZE:", len(graph_data_str))
        print(graph_data_str[:1000])  # First 1000 chars

        synthesis_prompt = self._prompt_manager.render(
            PromptType.SYNTHESIS,
            user_query=request.message,
            user_message=request.message,
            intent_name=intent.name,
            confidence=intent.confidence if intent.confidence is not None else 1.0,
            entities=json.dumps(entities_formatted, default=str),
            graph_result=graph_data_str,
        )

        # Step 6: Synthesize response via QuickMLClient call
        synthesis_messages = self._build_synthesis_messages(
            context=context,
            synthesis_prompt=synthesis_prompt,
            user_message=request.message,
        )
        llm_request = self._build_llm_request(synthesis_messages)
        llm_response = self._client.generate(llm_request)

        # Step 7: Return formatted ChatResponse with populated payload
        return self._build_chat_response(
            context=context,
            llm_response=llm_response,
            intent=intent,
            data=graph_data,
        )

    def _build_context(self, request: ChatRequest) -> ConversationContext:
        """Constructs a ConversationContext from the incoming ChatRequest."""
        conv_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        return ConversationContext(
            conversation_id=conv_id,
            case_id=request.case_id,
            history=list(request.history),
            metadata=dict(request.metadata),
        )

    def _build_messages(
        self, context: ConversationContext, user_message: str
    ) -> list[ChatMessage]:
        """Assembles default system prompt, history, and user message."""
        system_prompt = self._prompt_manager.get_prompt(PromptType.SYSTEM)
        system_msg = ChatMessage(role="system", content=system_prompt)
        user_msg = ChatMessage(role="user", content=user_message)

        messages: list[ChatMessage] = [system_msg]
        messages.extend(context.history)
        messages.append(user_msg)
        return messages

    def _build_synthesis_messages(
        self,
        context: ConversationContext,
        synthesis_prompt: str,
        user_message: str,
    ) -> list[ChatMessage]:
        """Assembles synthesis system prompt, history, and user message."""
        system_msg = ChatMessage(role="system", content=synthesis_prompt)
        user_msg = ChatMessage(role="user", content=user_message)

        messages: list[ChatMessage] = [system_msg]
        messages.extend(context.history)
        messages.append(user_msg)
        return messages

    def _build_llm_request(self, messages: list[ChatMessage]) -> LLMRequest:
        """Translates assembled messages into a provider-agnostic LLMRequest."""
        return LLMRequest(
            messages=messages,
            temperature=0.0,
            thinking=False,
        )

    def _build_chat_response(
        self,
        context: ConversationContext,
        llm_response: LLMResponse,
        intent: Intent | None = None,
        data: dict[str, Any] | None = None,
    ) -> ChatResponse:
        """Formats provider LLMResponse into the final presentation ChatResponse."""
        metadata: dict[str, Any] = {}
        if llm_response.finish_reason is not None:
            metadata["finish_reason"] = llm_response.finish_reason
        if llm_response.usage is not None:
            metadata["usage"] = llm_response.usage.model_dump()

        entities = intent.entities if intent is not None else []

        return ChatResponse(
            message=llm_response.content or "",
            conversation_id=context.conversation_id,
            intent=intent,
            entities=entities,
            data=data,
            metadata=metadata,
        )

    def _truncate_graph_data(self, data: Any, key_name: str = "") -> Any:
        """Recursively preprocesses graph payload to reduce prompt size for QuickML synthesis.

        - Preserves all summary statistics, counts, alert levels, and dictionary structures.
        - Limits lists of case IDs (keys containing 'case_id' or 'case_ids') to at most 5 entries.
        - Limits all other large collections/lists to at most 10 items.
        """
        if isinstance(data, dict):
            return {
                k: self._truncate_graph_data(v, key_name=k)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            is_case_id_list = "case_id" in key_name.lower() or "case_ids" in key_name.lower()
            limit = 5 if is_case_id_list else 10
            truncated_list = data[:limit]
            return [self._truncate_graph_data(item, key_name=key_name) for item in truncated_list]
        else:
            return data

    def _build_missing_entity_clarification(
        self, intent_name: str | None, entity_type: str
    ) -> str:
        """Builds a user-friendly clarification prompt when a required entity is missing."""
        if intent_name and intent_name in MISSING_ENTITY_CLARIFICATIONS:
            msg = MISSING_ENTITY_CLARIFICATIONS[intent_name].get(entity_type)
            if msg:
                return msg
        entity_label = entity_type.replace("_", " ")
        return (
            f"I need a {entity_label} to process this request.\n"
            f"Please specify a case identifier, for example:\n\n"
            f"    Show similar cases to FIR/BEL/0064"
        )


