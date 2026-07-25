"""tests/api/test_chat_route.py

Unit and integration tests for presentation layer router backend.app.api.routes.chat.
Verifies FastAPI HTTP transport, request validation, dependency overrides,
response serialization, domain exception mapping, and OpenAPI schema metadata.
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.ai.exceptions import (
    AIError,
    AIValidationError,
    PromptError,
    QuickMLAuthError,
    QuickMLConnectionError,
    QuickMLRateLimitError,
    QuickMLResponseError,
    QuickMLTimeoutError,
)
from backend.app.ai.quickml_service import QuickMLService
from backend.app.ai.schemas import ChatResponse, Entity, Intent
from backend.app.api.routes.chat import get_quickml_service
from backend.app.main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_quickml_service() -> MagicMock:
    service = MagicMock(spec=QuickMLService)
    service.chat.return_value = ChatResponse(
        message="Test assistant response",
        conversation_id="conv-test-999",
        intent=Intent(name="GET_CASE", confidence=0.98, entities=[Entity(type="case_id", value="CR-101")]),
        entities=[Entity(type="case_id", value="CR-101")],
        data={"case": {"id": "CR-101"}},
        metadata={"finish_reason": "stop", "usage": {"total_tokens": 20}},
    )
    return service


@pytest.fixture
def client(mock_quickml_service: MagicMock) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_quickml_service] = lambda: mock_quickml_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── Success Tests ─────────────────────────────────────────────────────────────

def test_chat_endpoint_success_returns_200(client: TestClient) -> None:
    # Arrange
    payload = {"message": "Show case CR-101"}

    # Act
    response = client.post("/api/chat", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK


def test_chat_endpoint_response_matches_chat_response_schema(
    client: TestClient,
) -> None:
    # Arrange
    payload = {"message": "Show case CR-101"}

    # Act
    response = client.post("/api/chat", json=payload)
    data = response.json()

    # Assert
    assert "message" in data
    assert "conversation_id" in data
    assert "intent" in data
    assert "entities" in data
    assert "data" in data
    assert "metadata" in data


def test_chat_endpoint_invokes_service_chat_exactly_once(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    payload = {"message": "Show hotspots"}

    # Act
    client.post("/api/chat", json=payload)

    # Assert
    mock_quickml_service.chat.assert_called_once()


# ── Request Validation Tests ──────────────────────────────────────────────────

def test_chat_endpoint_missing_message_returns_422(client: TestClient) -> None:
    # Arrange
    payload: dict = {}  # missing required 'message' key

    # Act
    response = client.post("/api/chat", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_endpoint_invalid_payload_returns_422(client: TestClient) -> None:
    # Arrange
    invalid_json_string = "not a valid json body"

    # Act
    response = client.post(
        "/api/chat",
        content=invalid_json_string,
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_endpoint_incorrect_field_types_returns_422(client: TestClient) -> None:
    # Arrange
    payload = {
        "message": "Valid query",
        "history": "should_be_a_list_not_a_string",
    }

    # Act
    response = client.post("/api/chat", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── Exception Mapping Tests ───────────────────────────────────────────────────

def test_chat_endpoint_quickml_auth_error_maps_to_401(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = QuickMLAuthError("Invalid OAuth Token")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication failed" in response.json()["detail"]


def test_chat_endpoint_quickml_rate_limit_error_maps_to_429(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = QuickMLRateLimitError("Limit exceeded")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "rate limit exceeded" in response.json()["detail"].lower()


def test_chat_endpoint_quickml_timeout_error_maps_to_504(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = QuickMLTimeoutError("Request timed out")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert "timed out" in response.json()["detail"].lower()


def test_chat_endpoint_quickml_connection_error_maps_to_503(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = QuickMLConnectionError("Network connection failed")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "unable to connect" in response.json()["detail"].lower()


def test_chat_endpoint_quickml_response_error_maps_to_502(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = QuickMLResponseError("Bad provider JSON")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "invalid response" in response.json()["detail"].lower()


def test_chat_endpoint_prompt_error_maps_to_500(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = PromptError("Prompt template missing")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "prompt template" in response.json()["detail"].lower()


def test_chat_endpoint_ai_validation_error_maps_to_400(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = AIValidationError("Payload invalid")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid ai request payload" in response.json()["detail"].lower()


def test_chat_endpoint_ai_error_maps_to_500(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    mock_quickml_service.chat.side_effect = AIError("Subsystem failure")

    # Act
    response = client.post("/api/chat", json={"message": "Hello"})

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "ai subsystem error" in response.json()["detail"].lower()


# ── Dependency Injection Tests ────────────────────────────────────────────────

def test_chat_endpoint_dependency_override_works(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    payload = {"message": "Test DI"}

    # Act
    client.post("/api/chat", json=payload)

    # Assert
    mock_quickml_service.chat.assert_called_once()


def test_chat_endpoint_injected_service_receives_chat_request_payload(
    client: TestClient, mock_quickml_service: MagicMock
) -> None:
    # Arrange
    payload = {"message": "Check repeat offenders", "case_id": "CR-99"}

    # Act
    client.post("/api/chat", json=payload)

    # Assert
    passed_request = mock_quickml_service.chat.call_args[0][0]
    assert passed_request.message == "Check repeat offenders"
    assert passed_request.case_id == "CR-99"


# ── Response Model Serialization Tests ────────────────────────────────────────

def test_chat_endpoint_serializes_message(client: TestClient) -> None:
    # Act
    response = client.post("/api/chat", json={"message": "Query"})

    # Assert
    assert response.json()["message"] == "Test assistant response"


def test_chat_endpoint_serializes_intent(client: TestClient) -> None:
    # Act
    response = client.post("/api/chat", json={"message": "Query"})

    # Assert
    intent = response.json()["intent"]
    assert intent["name"] == "GET_CASE"
    assert intent["confidence"] == 0.98


def test_chat_endpoint_serializes_entities(client: TestClient) -> None:
    # Act
    response = client.post("/api/chat", json={"message": "Query"})

    # Assert
    entities = response.json()["entities"]
    assert len(entities) == 1
    assert entities[0]["type"] == "case_id"
    assert entities[0]["value"] == "CR-101"


def test_chat_endpoint_serializes_metadata(client: TestClient) -> None:
    # Act
    response = client.post("/api/chat", json={"message": "Query"})

    # Assert
    metadata = response.json()["metadata"]
    assert metadata["finish_reason"] == "stop"
    assert metadata["usage"]["total_tokens"] == 20


def test_chat_endpoint_serializes_data(client: TestClient) -> None:
    # Act
    response = client.post("/api/chat", json={"message": "Query"})

    # Assert
    assert response.json()["data"] == {"case": {"id": "CR-101"}}


# ── OpenAPI Schema Tests ─────────────────────────────────────────────────────

def test_openapi_schema_contains_chat_route() -> None:
    # Arrange
    app = create_app()

    # Act
    openapi_schema = app.openapi()

    # Assert
    assert "/api/chat" in openapi_schema["paths"]


def test_openapi_schema_contains_post_operation() -> None:
    # Arrange
    app = create_app()

    # Act
    paths = app.openapi()["paths"]

    # Assert
    assert "post" in paths["/api/chat"]


def test_openapi_schema_documents_200_response() -> None:
    # Arrange
    app = create_app()

    # Act
    post_op = app.openapi()["paths"]["/api/chat"]["post"]

    # Assert
    assert "200" in post_op["responses"]
