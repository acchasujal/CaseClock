"""backend/app/ai/quickml_service.py

Application layer service orchestrating conversation context assembly,
prompt retrieval, QuickML client invocation, and ChatResponse formatting.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationContext,
    LLMRequest,
    LLMResponse,
)


class QuickMLService:
    """Application layer service orchestrating AI chat interactions."""

    def __init__(
        self,
        client: QuickMLClient,
        prompt_manager: PromptManager,
    ) -> None:
        """Initialize QuickMLService with injected client and prompt manager dependencies.
        
        Args:
            client: Infrastructure client for QuickML API execution.
            prompt_manager: Manager for prompt template retrieval and rendering.
        """
        self._client = client
        self._prompt_manager = prompt_manager

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Processes an incoming ChatRequest and returns a formatted ChatResponse.
        
        Args:
            request: Presentation layer ChatRequest payload.
            
        Returns:
            Presentation layer ChatResponse payload.
            
        Raises:
            QuickMLError: If the underlying QuickML client execution fails.
            PromptError: If system prompt retrieval fails.
            AIError: For generic AI subsystem failures.
        """
        context = self._build_context(request)
        messages = self._build_messages(context, request.message)
        llm_request = self._build_llm_request(messages)
        llm_response = self._client.generate(llm_request)
        return self._build_chat_response(context, llm_response)

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
        """Assembles prompt and history messages into a unified list."""
        system_prompt = self._prompt_manager.get_prompt(PromptType.SYSTEM)
        system_msg = ChatMessage(role="system", content=system_prompt)
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
        self, context: ConversationContext, llm_response: LLMResponse
    ) -> ChatResponse:
        """Formats provider LLMResponse into the final presentation ChatResponse."""
        metadata: dict[str, Any] = {}
        if llm_response.finish_reason is not None:
            metadata["finish_reason"] = llm_response.finish_reason
        if llm_response.usage is not None:
            metadata["usage"] = llm_response.usage.model_dump()

        return ChatResponse(
            message=llm_response.content or "",
            conversation_id=context.conversation_id,
            intent=None,
            entities=[],
            data=None,
            metadata=metadata,
        )
