"""tests/ai/test_quickml_service.py

Comprehensive unit tests for backend.app.ai.quickml_service.QuickMLService.
Verifies dependency injection, conversation context construction, intent extraction,
confidence validation, graph service dispatching, synthesis prompt rendering,
LLM message building, error propagation, and orchestration execution order.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from backend.app.ai.exceptions import (
    AIError,
    IntentExtractionError,
    PromptError,
    QuickMLError,
    ToolExecutionError,
)
from backend.app.ai.intent_dispatcher import IntentDispatcher, IntentName
from backend.app.ai.intent_extractor import IntentExtractor
from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.quickml_service import QuickMLService
from backend.app.ai.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationContext,
    Entity,
    Intent,
    LLMRequest,
    LLMResponse,
    UsageMetadata,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=QuickMLClient)
    client.generate.return_value = LLMResponse(
        content="Assistant response text",
        finish_reason="stop",
        usage=UsageMetadata(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    return client


@pytest.fixture
def mock_prompt_manager() -> MagicMock:
    pm = MagicMock(spec=PromptManager)
    pm.get_prompt.return_value = "System prompt template"
    pm.render.return_value = "Rendered synthesis prompt"
    return pm


@pytest.fixture
def mock_extractor() -> MagicMock:
    extractor = MagicMock(spec=IntentExtractor)
    extractor.extract.return_value = Intent(
        name="GET_HOTSPOTS",
        confidence=0.95,
        entities=[Entity(type="zone", value="North Zone")],
    )
    return extractor


@pytest.fixture
def mock_dispatcher() -> MagicMock:
    dispatcher = MagicMock(spec=IntentDispatcher)
    dispatcher.dispatch.return_value = {"hotspots": ["Station A", "Station B"]}
    return dispatcher


@pytest.fixture
def service(
    mock_client: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
) -> QuickMLService:
    return QuickMLService(
        client=mock_client,
        prompt_manager=mock_prompt_manager,
        intent_extractor=mock_extractor,
        intent_dispatcher=mock_dispatcher,
        min_confidence_threshold=0.60,
    )


# ── Constructor Tests ─────────────────────────────────────────────────────────

def test_constructor_injected_intent_extractor_used(
    mock_client: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_extractor: MagicMock,
) -> None:
    # Act
    service = QuickMLService(
        client=mock_client,
        prompt_manager=mock_prompt_manager,
        intent_extractor=mock_extractor,
    )

    # Assert
    assert service._intent_extractor is mock_extractor


def test_constructor_injected_intent_dispatcher_used(
    mock_client: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_dispatcher: MagicMock,
) -> None:
    # Act
    service = QuickMLService(
        client=mock_client,
        prompt_manager=mock_prompt_manager,
        intent_dispatcher=mock_dispatcher,
    )

    # Assert
    assert service._intent_dispatcher is mock_dispatcher


def test_constructor_default_intent_extractor_constructed_when_none(
    mock_client: MagicMock, mock_prompt_manager: MagicMock
) -> None:
    # Act
    service = QuickMLService(client=mock_client, prompt_manager=mock_prompt_manager)

    # Assert
    assert isinstance(service._intent_extractor, IntentExtractor)


def test_constructor_default_intent_dispatcher_constructed_when_none(
    mock_client: MagicMock, mock_prompt_manager: MagicMock
) -> None:
    # Act
    service = QuickMLService(client=mock_client, prompt_manager=mock_prompt_manager)

    # Assert
    assert isinstance(service._intent_dispatcher, IntentDispatcher)


def test_constructor_confidence_threshold_stored(
    mock_client: MagicMock, mock_prompt_manager: MagicMock
) -> None:
    # Act
    service = QuickMLService(
        client=mock_client,
        prompt_manager=mock_prompt_manager,
        min_confidence_threshold=0.75,
    )

    # Assert
    assert service._min_confidence_threshold == 0.75


# ── Context Tests ──────────────────────────────────────────────────────────────

def test_build_context_preserves_conversation_id(service: QuickMLService) -> None:
    # Arrange
    request = ChatRequest(message="Hello", conversation_id="conv-explicit-123")

    # Act
    context = service._build_context(request)

    # Assert
    assert context.conversation_id == "conv-explicit-123"


def test_build_context_autogenerates_conversation_id_when_missing(
    service: QuickMLService,
) -> None:
    # Arrange
    request = ChatRequest(message="Hello", conversation_id=None)

    # Act
    context = service._build_context(request)

    # Assert
    assert context.conversation_id.startswith("conv-")
    assert len(context.conversation_id) > 5


def test_build_context_copies_history(service: QuickMLService) -> None:
    # Arrange
    history = [ChatMessage(role="user", content="Past question")]
    request = ChatRequest(message="Hello", history=history)

    # Act
    context = service._build_context(request)

    # Assert
    assert len(context.history) == 1
    assert context.history[0].content == "Past question"


def test_build_context_copies_metadata(service: QuickMLService) -> None:
    # Arrange
    request = ChatRequest(message="Hello", metadata={"source": "mobile"})

    # Act
    context = service._build_context(request)

    # Assert
    assert context.metadata == {"source": "mobile"}


def test_build_context_copies_case_id(service: QuickMLService) -> None:
    # Arrange
    request = ChatRequest(message="Hello", case_id="CR-2026-99")

    # Act
    context = service._build_context(request)

    # Assert
    assert context.case_id == "CR-2026-99"


# ── Message Builders Tests ────────────────────────────────────────────────────

def test_build_messages_contains_system_history_user(
    service: QuickMLService, mock_prompt_manager: MagicMock
) -> None:
    # Arrange
    context = ConversationContext(
        conversation_id="c1",
        history=[ChatMessage(role="user", content="Prev question")],
    )

    # Act
    messages = service._build_messages(context, "Current question")

    # Assert
    mock_prompt_manager.get_prompt.assert_called_once_with(PromptType.SYSTEM)
    assert len(messages) == 3
    assert messages[0].role == "system"
    assert messages[0].content == "System prompt template"
    assert messages[1].content == "Prev question"
    assert messages[2].role == "user"
    assert messages[2].content == "Current question"


def test_build_synthesis_messages_contains_synthesis_history_user(
    service: QuickMLService,
) -> None:
    # Arrange
    context = ConversationContext(
        conversation_id="c1",
        history=[ChatMessage(role="user", content="Prev question")],
    )

    # Act
    messages = service._build_synthesis_messages(
        context, "Rendered synthesis system prompt", "Current question"
    )

    # Assert
    assert len(messages) == 3
    assert messages[0].role == "system"
    assert messages[0].content == "Rendered synthesis system prompt"
    assert messages[1].content == "Prev question"
    assert messages[2].role == "user"
    assert messages[2].content == "Current question"


def test_build_llm_request_creates_expected_request(service: QuickMLService) -> None:
    # Arrange
    messages = [ChatMessage(role="user", content="Test")]

    # Act
    llm_req = service._build_llm_request(messages)

    # Assert
    assert isinstance(llm_req, LLMRequest)
    assert llm_req.messages == messages
    assert llm_req.temperature == 0.0
    assert llm_req.thinking is False


# ── General Chat & Bypass Flow Tests ─────────────────────────────────────────

def test_chat_general_chat_bypass(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_client: MagicMock,
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GENERAL_CHAT", confidence=1.0, entities=[])
    request = ChatRequest(message="Hello there")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "GENERAL_CHAT"
    assert response.data is None
    mock_dispatcher.dispatch.assert_not_called()
    mock_prompt_manager.render.assert_not_called()
    mock_client.generate.assert_called_once()


def test_chat_unknown_bypass(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_client: MagicMock,
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="UNKNOWN", confidence=0.2, entities=[])
    request = ChatRequest(message="Random noise")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "UNKNOWN"
    assert response.data is None
    mock_dispatcher.dispatch.assert_not_called()
    mock_prompt_manager.render.assert_not_called()
    mock_client.generate.assert_called_once()


def test_chat_low_confidence_downgraded_to_unknown_bypass(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
) -> None:
    # Arrange
    # Confidence 0.40 < 0.60 threshold
    mock_extractor.extract.return_value = Intent(name="GET_HOTSPOTS", confidence=0.40, entities=[])
    request = ChatRequest(message="Hotspots?")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "UNKNOWN"
    assert response.data is None
    mock_dispatcher.dispatch.assert_not_called()


# ── Graph Flow Tests ──────────────────────────────────────────────────────────

def test_chat_graph_flow_execution(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_client: MagicMock,
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(
        name="GET_HOTSPOTS",
        confidence=0.95,
        entities=[Entity(type="zone", value="North Zone")],
    )
    mock_dispatcher.dispatch.return_value = {"hotspot_count": 3}
    request = ChatRequest(message="Show hotspots in North Zone")

    # Act
    response = service.chat(request)

    # Assert
    mock_dispatcher.dispatch.assert_called_once()
    mock_prompt_manager.render.assert_called_once()
    assert mock_prompt_manager.render.call_args[1]["intent_name"] == "GET_HOTSPOTS"
    assert mock_prompt_manager.render.call_args[1]["confidence"] == 0.95
    mock_client.generate.assert_called_once()

    assert response.intent.name == "GET_HOTSPOTS"
    assert response.data == {"hotspot_count": 3}
    assert len(response.entities) == 1
    assert response.entities[0].type == "zone"
    assert response.entities[0].value == "North Zone"
    assert response.metadata["finish_reason"] == "stop"
    assert response.metadata["usage"]["total_tokens"] == 15


# ── Confidence Tests ──────────────────────────────────────────────────────────

def test_confidence_above_threshold_retains_intent(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GET_CASE", confidence=0.90, entities=[])
    request = ChatRequest(message="Show case")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "GET_CASE"


def test_confidence_equal_threshold_retains_intent(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GET_CASE", confidence=0.60, entities=[])
    request = ChatRequest(message="Show case")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "GET_CASE"


def test_confidence_below_threshold_downgrades_intent(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GET_CASE", confidence=0.59, entities=[])
    request = ChatRequest(message="Show case")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "UNKNOWN"


def test_confidence_none_retains_intent(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GET_CASE", confidence=None, entities=[])
    request = ChatRequest(message="Show case")

    # Act
    response = service.chat(request)

    # Assert
    assert response.intent.name == "GET_CASE"


# ── Exception Propagation Tests ───────────────────────────────────────────────

def test_chat_extractor_exception_propagates(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.side_effect = IntentExtractionError("Extractor failed")

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        service.chat(ChatRequest(message="Test"))

    assert "extractor failed" in str(exc_info.value).lower()


def test_chat_dispatcher_exception_propagates(
    service: QuickMLService, mock_dispatcher: MagicMock
) -> None:
    # Arrange
    mock_dispatcher.dispatch.side_effect = ToolExecutionError("Dispatcher failed")

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        service.chat(ChatRequest(message="Test"))

    assert "dispatcher failed" in str(exc_info.value).lower()


def test_chat_prompt_exception_propagates(
    service: QuickMLService, mock_prompt_manager: MagicMock
) -> None:
    # Arrange
    mock_prompt_manager.render.side_effect = PromptError("Synthesis template missing")

    # Act & Assert
    with pytest.raises(PromptError) as exc_info:
        service.chat(ChatRequest(message="Test"))

    assert "synthesis template missing" in str(exc_info.value).lower()


def test_chat_quickml_client_exception_propagates(
    service: QuickMLService, mock_client: MagicMock
) -> None:
    # Arrange
    mock_client.generate.side_effect = QuickMLError("API Rate Limit")

    # Act & Assert
    with pytest.raises(QuickMLError) as exc_info:
        service.chat(ChatRequest(message="Test"))

    assert "rate limit" in str(exc_info.value).lower()


def test_chat_unexpected_exception_propagates(
    service: QuickMLService, mock_extractor: MagicMock
) -> None:
    # Arrange
    mock_extractor.extract.side_effect = RuntimeError("System Memory Crash")

    # Act & Assert
    with pytest.raises(RuntimeError) as exc_info:
        service.chat(ChatRequest(message="Test"))

    assert "system memory crash" in str(exc_info.value).lower()


# ── Chat Response Tests ───────────────────────────────────────────────────────

def test_build_chat_response_populates_metadata_when_present(
    service: QuickMLService,
) -> None:
    # Arrange
    context = ConversationContext(conversation_id="c123")
    llm_resp = LLMResponse(
        content="Response text",
        finish_reason="stop",
        usage=UsageMetadata(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    intent = Intent(name="GET_CASE", entities=[Entity(type="case_id", value="C1")])

    # Act
    resp = service._build_chat_response(context, llm_resp, intent=intent, data={"key": "val"})

    # Assert
    assert resp.message == "Response text"
    assert resp.conversation_id == "c123"
    assert resp.intent == intent
    assert resp.entities == [Entity(type="case_id", value="C1")]
    assert resp.data == {"key": "val"}
    assert resp.metadata["finish_reason"] == "stop"
    assert resp.metadata["usage"] == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


def test_build_chat_response_metadata_empty_when_none(service: QuickMLService) -> None:
    # Arrange
    context = ConversationContext(conversation_id="c123")
    llm_resp = LLMResponse(content="Response text", finish_reason=None, usage=None)

    # Act
    resp = service._build_chat_response(context, llm_resp)

    # Assert
    assert resp.metadata == {}


def test_build_chat_response_empty_message_defaults_to_empty_string(
    service: QuickMLService,
) -> None:
    # Arrange
    context = ConversationContext(conversation_id="c123")
    llm_resp = LLMResponse(content=None)

    # Act
    resp = service._build_chat_response(context, llm_resp)

    # Assert
    assert resp.message == ""


# ── Orchestration Order Tests ─────────────────────────────────────────────────

def test_orchestration_execution_order_for_graph_intent(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_client: MagicMock,
) -> None:
    # Arrange
    manager_tracker = MagicMock()
    manager_tracker.attach_mock(mock_extractor.extract, "extract")
    manager_tracker.attach_mock(mock_dispatcher.dispatch, "dispatch")
    manager_tracker.attach_mock(mock_prompt_manager.render, "render")
    manager_tracker.attach_mock(mock_client.generate, "generate")

    # Act
    service.chat(ChatRequest(message="Show hotspots"))

    # Assert
    expected_calls = [
        call.extract("Show hotspots"),
        call.dispatch(mock_extractor.extract.return_value),
        call.render(
            PromptType.SYNTHESIS,
            user_query="Show hotspots",
            user_message="Show hotspots",
            intent_name="GET_HOTSPOTS",
            confidence=0.95,
            entities='[{"type": "zone", "value": "North Zone"}]',
            graph_result=json.dumps({"hotspots": ["Station A", "Station B"]}, indent=2, default=str),
        ),
        call.generate(service._build_llm_request(service._build_synthesis_messages(
            ConversationContext(conversation_id="dummy"),
            "Rendered synthesis prompt",
            "Show hotspots"
        ))),
    ]

    # Verify method call order
    call_names = [call_item[0] for call_item in manager_tracker.mock_calls]
    assert call_names == ["extract", "dispatch", "render", "generate"]


def test_orchestration_execution_order_for_general_chat(
    service: QuickMLService,
    mock_extractor: MagicMock,
    mock_dispatcher: MagicMock,
    mock_prompt_manager: MagicMock,
    mock_client: MagicMock,
) -> None:
    # Arrange
    mock_extractor.extract.return_value = Intent(name="GENERAL_CHAT", confidence=1.0, entities=[])
    manager_tracker = MagicMock()
    manager_tracker.attach_mock(mock_extractor.extract, "extract")
    manager_tracker.attach_mock(mock_dispatcher.dispatch, "dispatch")
    manager_tracker.attach_mock(mock_prompt_manager.render, "render")
    manager_tracker.attach_mock(mock_client.generate, "generate")

    # Act
    service.chat(ChatRequest(message="Hello"))

    # Assert
    call_names = [call_item[0] for call_item in manager_tracker.mock_calls]
    assert call_names == ["extract", "generate"]
    mock_dispatcher.dispatch.assert_not_called()
    mock_prompt_manager.render.assert_not_called()
