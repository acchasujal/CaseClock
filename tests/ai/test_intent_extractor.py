"""tests/ai/test_intent_extractor.py

Comprehensive unit tests for backend.app.ai.intent_extractor.IntentExtractor.
Verifies public API, LLM request construction, JSON extraction (fence-aware, regex-free),
jsonschema validation, entity parsing, intent model building, and exception handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.app.ai.exceptions import IntentExtractionError
from backend.app.ai.intent_extractor import IntentExtractor
from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.schemas import Entity, Intent, LLMResponse


# ── Sample Fixture Schemas and Prompts ────────────────────────────────────────

@pytest.fixture
def valid_intent_schema() -> dict:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "GET_CASE",
                    "GET_CASE_DETAILS",
                    "GET_SIMILAR_CASES",
                    "GET_REPEAT_OFFENDERS",
                    "GET_NETWORK",
                    "GET_HOTSPOTS",
                    "GET_DEPENDENCIES",
                    "GET_CLOCK",
                    "GENERAL_CHAT",
                    "UNKNOWN",
                ],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["type", "value"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["intent", "entities"],
        "additionalProperties": False,
    }


@pytest.fixture
def mock_dependencies(valid_intent_schema: dict) -> tuple[MagicMock, MagicMock]:
    mock_client = MagicMock(spec=QuickMLClient)
    mock_pm = MagicMock(spec=PromptManager)
    mock_pm.get_prompt.return_value = "System intent prompt instructions"
    mock_pm.get_schema.return_value = valid_intent_schema
    return mock_client, mock_pm


# ── Public API Tests ──────────────────────────────────────────────────────────

def test_extract_successful_intent_returns_intent_model(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    payload = {
        "intent": "GET_HOTSPOTS",
        "confidence": 0.95,
        "entities": [{"type": "zone", "value": "North Zone"}],
    }
    mock_client.generate.return_value = LLMResponse(content=json.dumps(payload))
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    intent = extractor.extract("Show crime hotspots in North Zone")

    # Assert
    assert isinstance(intent, Intent)
    assert intent.name == "GET_HOTSPOTS"
    assert intent.confidence == 0.95
    assert len(intent.entities) == 1
    assert intent.entities[0].type == "zone"
    assert intent.entities[0].value == "North Zone"


def test_extract_empty_user_message_raises_intent_extraction_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor.extract("   ")

    assert "empty user message" in str(exc_info.value).lower()


def test_extract_quickml_provider_exception_raises_intent_extraction_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    mock_client.generate.side_effect = RuntimeError("QuickML API Timeout")
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor.extract("Check repeat offenders")

    assert "provider failure" in str(exc_info.value).lower()
    assert exc_info.value.__cause__ is not None


def test_extract_empty_llm_response_raises_intent_extraction_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    mock_client.generate.return_value = LLMResponse(content="")
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor.extract("Hello")

    assert "empty" in str(exc_info.value).lower()


def test_extract_malformed_json_raises_intent_extraction_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    mock_client.generate.return_value = LLMResponse(content="not a json string")
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor.extract("Check status")

    assert "not valid json" in str(exc_info.value).lower()


def test_extract_schema_validation_failure_raises_intent_extraction_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    invalid_payload = {"intent": "INVALID_INTENT_NAME", "entities": []}
    mock_client.generate.return_value = LLMResponse(content=json.dumps(invalid_payload))
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor.extract("What is this?")

    assert "failed schema validation" in str(exc_info.value).lower()


def test_extract_successful_extraction_with_no_entities(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    payload = {"intent": "GENERAL_CHAT", "confidence": 1.0, "entities": []}
    mock_client.generate.return_value = LLMResponse(content=json.dumps(payload))
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    intent = extractor.extract("Hi there")

    # Assert
    assert intent.name == "GENERAL_CHAT"
    assert intent.entities == []


def test_extract_confidence_parsed_correctly(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    payload = {"intent": "GET_CASE", "confidence": 0.88, "entities": [{"type": "case_id", "value": "CR-101"}]}
    mock_client.generate.return_value = LLMResponse(content=json.dumps(payload))
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    intent = extractor.extract("Show CR-101")

    # Assert
    assert intent.confidence == 0.88


def test_extract_missing_confidence_results_in_none(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    payload = {"intent": "UNKNOWN", "entities": []}
    mock_client.generate.return_value = LLMResponse(content=json.dumps(payload))
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    intent = extractor.extract("Random text")

    # Assert
    assert intent.name == "UNKNOWN"
    assert intent.confidence is None


# ── Request Building Tests ────────────────────────────────────────────────────

def test_build_request_uses_system_prompt_from_prompt_manager(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    request = extractor._build_request("User query text")

    # Assert
    mock_pm.get_prompt.assert_called_once_with(PromptType.INTENT)
    assert request.messages[0].role == "system"
    assert request.messages[0].content == "System intent prompt instructions"


def test_build_request_creates_system_and_user_messages(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    request = extractor._build_request("Find similar cases")

    # Assert
    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"
    assert request.messages[1].content == "Find similar cases"


def test_build_request_sets_temperature_to_zero(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    request = extractor._build_request("Test prompt")

    # Assert
    assert request.temperature == 0.0


def test_build_request_sets_thinking_to_false(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    request = extractor._build_request("Test prompt")

    # Assert
    assert request.thinking is False


def test_build_request_contains_exactly_two_messages(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)

    # Act
    request = extractor._build_request("Test prompt")

    # Assert
    assert len(request.messages) == 2


# ── JSON Extraction Tests ─────────────────────────────────────────────────────

def test_extract_json_plain_json(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    response = LLMResponse(content='{"intent": "GET_CASE", "entities": []}')

    # Act
    result = extractor._extract_json(response)

    # Assert
    assert result == {"intent": "GET_CASE", "entities": []}


def test_extract_json_fenced_json_with_json_language_tag(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    fenced_content = "```json\n{\n  \"intent\": \"GET_CLOCK\",\n  \"entities\": []\n}\n```"
    response = LLMResponse(content=fenced_content)

    # Act
    result = extractor._extract_json(response)

    # Assert
    assert result == {"intent": "GET_CLOCK", "entities": []}


def test_extract_json_fenced_json_generic_markdown(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    fenced_content = "```\n{\"intent\": \"GET_HOTSPOTS\", \"entities\": []}\n```"
    response = LLMResponse(content=fenced_content)

    # Act
    result = extractor._extract_json(response)

    # Assert
    assert result == {"intent": "GET_HOTSPOTS", "entities": []}


def test_extract_json_malformed_json_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    response = LLMResponse(content='{"intent": "GET_CASE",}')

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._extract_json(response)

    assert "not valid json" in str(exc_info.value).lower()


def test_extract_json_top_level_json_list_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    response = LLMResponse(content='[{"intent": "GET_CASE"}]')

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._extract_json(response)

    assert "top-level object" in str(exc_info.value).lower()


def test_extract_json_empty_response_content_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    response = LLMResponse(content=None)

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._extract_json(response)

    assert "content is empty" in str(exc_info.value).lower()


# ── Schema Validation Tests ───────────────────────────────────────────────────

def test_validate_schema_valid_payload(
    mock_dependencies: tuple[MagicMock, MagicMock],
    valid_intent_schema: dict,
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    payload = {"intent": "GET_REPEAT_OFFENDERS", "entities": []}

    # Act
    result = extractor._validate_schema(payload, valid_intent_schema)

    # Assert
    assert result == payload


def test_validate_schema_invalid_payload_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
    valid_intent_schema: dict,
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    invalid_payload = {"intent": "NON_EXISTENT_INTENT", "entities": []}

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._validate_schema(invalid_payload, valid_intent_schema)

    assert "failed schema validation" in str(exc_info.value).lower()


def test_validate_schema_malformed_schema_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    malformed_schema = {"type": "invalid_json_type_keyword"}
    payload = {"intent": "GET_CASE", "entities": []}

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._validate_schema(payload, malformed_schema)

    assert "schema itself is malformed" in str(exc_info.value).lower()


# ── Entity Parsing Tests ──────────────────────────────────────────────────────

def test_parse_entities_one_entity(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    raw_entities = [{"type": "case_id", "value": "CR-2026-999"}]

    # Act
    entities = extractor._parse_entities(raw_entities)

    # Assert
    assert len(entities) == 1
    assert isinstance(entities[0], Entity)
    assert entities[0].type == "case_id"
    assert entities[0].value == "CR-2026-999"


def test_parse_entities_multiple_entities(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    raw_entities = [
        {"type": "case_id", "value": "CR-2026-999"},
        {"type": "officer_id", "value": "officer-42"},
    ]

    # Act
    entities = extractor._parse_entities(raw_entities)

    # Assert
    assert len(entities) == 2
    assert entities[0].type == "case_id"
    assert entities[1].type == "officer_id"


def test_parse_entities_invalid_entity_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    raw_entities = ["invalid_non_dict_entity"]

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._parse_entities(raw_entities)

    assert "failed to construct entity" in str(exc_info.value).lower()


def test_parse_entities_missing_type_or_value_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    raw_entities = [{"type": "case_id"}]  # missing 'value'

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._parse_entities(raw_entities)

    assert "failed to construct entity" in str(exc_info.value).lower()


# ── Intent Building Tests ─────────────────────────────────────────────────────

def test_build_intent_complete_payload(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    validated = {
        "intent": "GET_DEPENDENCIES",
        "confidence": 0.99,
        "entities": [{"type": "case_id", "value": "CR-2026-555"}],
    }

    # Act
    intent = extractor._build_intent(validated)

    # Assert
    assert intent.name == "GET_DEPENDENCIES"
    assert intent.confidence == 0.99
    assert len(intent.entities) == 1
    assert intent.entities[0].type == "case_id"
    assert intent.entities[0].value == "CR-2026-555"


def test_build_intent_payload_without_confidence(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    validated = {
        "intent": "GENERAL_CHAT",
        "entities": [],
    }

    # Act
    intent = extractor._build_intent(validated)

    # Assert
    assert intent.name == "GENERAL_CHAT"
    assert intent.confidence is None
    assert intent.entities == []


def test_build_intent_invalid_confidence_raises_error(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    validated = {
        "intent": "GET_CASE",
        "confidence": "not_a_number",
        "entities": [],
    }

    # Act & Assert
    with pytest.raises(IntentExtractionError) as exc_info:
        extractor._build_intent(validated)

    assert "failed to construct intent model" in str(exc_info.value).lower()


def test_build_intent_empty_entities(
    mock_dependencies: tuple[MagicMock, MagicMock],
) -> None:
    # Arrange
    mock_client, mock_pm = mock_dependencies
    extractor = IntentExtractor(client=mock_client, prompt_manager=mock_pm)
    validated = {
        "intent": "UNKNOWN",
        "confidence": 0.5,
        "entities": [],
    }

    # Act
    intent = extractor._build_intent(validated)

    # Assert
    assert intent.name == "UNKNOWN"
    assert intent.entities == []
