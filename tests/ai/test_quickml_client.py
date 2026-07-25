"""tests/ai/test_quickml_client.py

Comprehensive unit tests for backend.app.ai.quickml_client.QuickMLClient.
Verifies HTTP header construction, payload translation, requests execution,
response parsing, error mapping, and full pipeline generation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from backend.app.ai.exceptions import (
    QuickMLAuthError,
    QuickMLConnectionError,
    QuickMLRateLimitError,
    QuickMLResponseError,
    QuickMLTimeoutError,
)
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.schemas import ChatMessage, LLMRequest, LLMResponse, UsageMetadata
from backend.app.db.catalyst import CatalystRestDatastore


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_datastore() -> MagicMock:
    ds = MagicMock(spec=CatalystRestDatastore)
    ds.access_token.return_value = "mock_oauth_token_123"
    ds.api_domain = "https://api.catalyst.zoho.in"
    ds.project_id = "999888777"
    ds.timeout = 30
    return ds


@pytest.fixture
def client(mock_datastore: MagicMock) -> QuickMLClient:
    return QuickMLClient(
        datastore=mock_datastore,
        default_model="crm-di-glm47b_30b_it",
        timeout=30,
        org_id="ORG_TEST_123",
    )


@pytest.fixture
def sample_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            ChatMessage(role="system", content="You are an AI assistant."),
            ChatMessage(role="user", content="Hello AI"),
        ],
        temperature=0.0,
        thinking=False,
    )


# ── Header Construction Tests ────────────────────────────────────────────────

def test_headers_oauth_token_added_correctly(client: QuickMLClient) -> None:
    # Act
    headers = client._build_headers()

    # Assert
    assert headers["Authorization"] == "Zoho-oauthtoken mock_oauth_token_123"


def test_headers_catalyst_org_added(client: QuickMLClient) -> None:
    # Act
    headers = client._build_headers()

    # Assert
    assert headers["CATALYST-ORG"] == "ORG_TEST_123"


def test_headers_content_type_present(client: QuickMLClient) -> None:
    # Act
    headers = client._build_headers()

    # Assert
    assert headers["Content-Type"] == "application/json"


def test_headers_oauth_failure_raises_quickml_auth_error(
    mock_datastore: MagicMock,
) -> None:
    # Arrange
    mock_datastore.access_token.side_effect = Exception("OAuth service unavailable")
    client = QuickMLClient(datastore=mock_datastore, org_id="ORG_123")

    # Act & Assert
    with pytest.raises(QuickMLAuthError) as exc_info:
        client._build_headers()

    assert "failed to acquire catalyst oauth access token" in str(exc_info.value).lower()


def test_headers_missing_org_id_raises_quickml_auth_error(
    mock_datastore: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("CATALYST_ORG", raising=False)
    monkeypatch.delenv("CATALYST_ORG_ID", raising=False)
    client = QuickMLClient(datastore=mock_datastore, org_id="")

    # Act & Assert
    with pytest.raises(QuickMLAuthError) as exc_info:
        client._build_headers()

    assert "missing catalyst-org" in str(exc_info.value).lower()


# ── Payload Translation Tests ────────────────────────────────────────────────

def test_payload_default_model_used_when_none(
    client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Act
    payload = client._build_payload(sample_request)

    # Assert
    assert payload["model"] == "crm-di-glm47b_30b_it"


def test_payload_model_override_used(
    client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    sample_request.model = "custom_model_v2"

    # Act
    payload = client._build_payload(sample_request)

    # Assert
    assert payload["model"] == "custom_model_v2"


def test_payload_message_serialization(
    client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Act
    payload = client._build_payload(sample_request)

    # Assert
    assert len(payload["messages"]) == 2
    assert payload["messages"][0] == {"role": "system", "content": "You are an AI assistant."}
    assert payload["messages"][1] == {"role": "user", "content": "Hello AI"}


def test_payload_message_name_included_if_present(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi", name="OfficerSmith")],
        temperature=0.0,
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["messages"][0]["name"] == "OfficerSmith"


def test_payload_temperature_copied(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        temperature=0.7,
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["temperature"] == 0.7


def test_payload_thinking_maps_to_enable_thinking(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        thinking=True,
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["chat_template_kwargs"]["enable_thinking"] is True


def test_payload_max_tokens_included_if_present(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        max_tokens=512,
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["max_tokens"] == 512


def test_payload_tools_included_if_present(client: QuickMLClient) -> None:
    # Arrange
    tools_def = [{"type": "function", "function": {"name": "get_weather"}}]
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        tools=tools_def,
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["tools"] == tools_def


def test_payload_response_format_included_if_present(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        response_format="json",
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["response_format"] == "json"


def test_payload_allowed_extra_kwargs_merged(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Hi")],
        extra_kwargs={"top_p": 0.9, "presence_penalty": 0.5},
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["top_p"] == 0.9
    assert payload["presence_penalty"] == 0.5


def test_payload_protected_keys_cannot_be_overridden(client: QuickMLClient) -> None:
    # Arrange
    request = LLMRequest(
        messages=[ChatMessage(role="user", content="Original message")],
        model="original_model",
        extra_kwargs={
            "model": "malicious_override",
            "messages": [{"role": "user", "content": "hacked"}],
            "temperature": 1.9,
        },
    )

    # Act
    payload = client._build_payload(request)

    # Assert
    assert payload["model"] == "original_model"
    assert payload["messages"][0]["content"] == "Original message"


# ── HTTP Request Tests ───────────────────────────────────────────────────────

@patch("requests.post")
def test_http_request_correct_url(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "OK"}
    mock_post.return_value = mock_resp

    # Act
    client.generate(sample_request)

    # Assert
    expected_url = "https://api.catalyst.zoho.in/quickml/v1/project/999888777/glm/chat"
    assert mock_post.call_args[0][0] == expected_url


@patch("requests.post")
def test_http_request_post_called_exactly_once(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "OK"}
    mock_post.return_value = mock_resp

    # Act
    client.generate(sample_request)

    # Assert
    mock_post.assert_called_once()


@patch("requests.post")
def test_http_request_timeout_passed(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "OK"}
    mock_post.return_value = mock_resp

    # Act
    client.generate(sample_request)

    # Assert
    assert mock_post.call_args[1]["timeout"] == 30


@patch("requests.post")
def test_http_request_headers_passed(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "OK"}
    mock_post.return_value = mock_resp

    # Act
    client.generate(sample_request)

    # Assert
    headers = mock_post.call_args[1]["headers"]
    assert headers["Authorization"] == "Zoho-oauthtoken mock_oauth_token_123"
    assert headers["CATALYST-ORG"] == "ORG_TEST_123"


@patch("requests.post")
def test_http_request_payload_passed(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "OK"}
    mock_post.return_value = mock_resp

    # Act
    client.generate(sample_request)

    # Assert
    json_payload = mock_post.call_args[1]["json"]
    assert json_payload["model"] == "crm-di-glm47b_30b_it"


# ── Response Parsing Tests ────────────────────────────────────────────────────

def test_parse_response_top_level_response_field(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {"response": "Text output from model"}

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.content == "Text output from model"


def test_parse_response_choices_message_content(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "choices": [
            {"message": {"role": "assistant", "content": "Content from choice message"}}
        ]
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.content == "Content from choice message"


def test_parse_response_usage_metadata(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "response": "Hello",
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        },
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.usage == UsageMetadata(prompt_tokens=12, completion_tokens=8, total_tokens=20)


def test_parse_response_finish_reason(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "response": "Hello",
        "finish_reason": "stop",
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.finish_reason == "stop"


def test_parse_response_missing_finish_reason_is_none(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {"response": "Hello"}

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.finish_reason is None


def test_parse_response_top_level_tool_calls(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "tool_calls": [
            {
                "id": "call_001",
                "name": "get_case_details",
                "arguments": '{"case_id": "CR-101"}',
            }
        ]
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "get_case_details"
    assert res.tool_calls[0].arguments == {"case_id": "CR-101"}
    assert res.tool_calls[0].call_id == "call_001"


def test_parse_response_nested_tool_calls(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_002",
                            "function": {
                                "name": "get_hotspots",
                                "arguments": {"zone": "North"},
                            },
                        }
                    ]
                }
            }
        ]
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "get_hotspots"
    assert res.tool_calls[0].arguments == {"zone": "North"}


def test_parse_response_json_string_tool_arguments(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "tool_calls": [
            {
                "name": "search_cases",
                "arguments": '{"query": "robbery", "top_k": 5}',
            }
        ]
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.tool_calls[0].arguments == {"query": "robbery", "top_k": 5}


def test_parse_response_invalid_json_tool_arguments(client: QuickMLClient) -> None:
    # Arrange
    raw_resp = {
        "tool_calls": [
            {
                "name": "search_cases",
                "arguments": "invalid json string",
            }
        ]
    }

    # Act
    res = client._parse_response(raw_resp)

    # Assert
    assert res.tool_calls[0].arguments == {"raw": "invalid json string"}


def test_parse_response_missing_content_and_tool_calls_raises_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    raw_resp = {"other_key": "val"}

    # Act & Assert
    with pytest.raises(QuickMLResponseError) as exc_info:
        client._parse_response(raw_resp)

    assert "missing both 'response' text and 'choices[0].message.content'" in str(exc_info.value).lower()


# ── Error Mapping Tests ───────────────────────────────────────────────────────

def test_map_error_timeout_raises_quickml_timeout_error(client: QuickMLClient) -> None:
    # Arrange
    exc = requests.exceptions.Timeout("Connection timed out")

    # Act
    mapped = client._map_error(exc)

    # Assert
    assert isinstance(mapped, QuickMLTimeoutError)
    assert "timed out" in str(mapped).lower()


def test_map_error_connection_error_raises_quickml_connection_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    exc = requests.exceptions.ConnectionError("Failed to connect")

    # Act
    mapped = client._map_error(exc)

    # Assert
    assert isinstance(mapped, QuickMLConnectionError)
    assert "connection failed" in str(mapped).lower()


def test_map_error_ssl_error_raises_quickml_connection_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    exc = requests.exceptions.SSLError("Certificate verify failed")

    # Act
    mapped = client._map_error(exc)

    # Assert
    assert isinstance(mapped, QuickMLConnectionError)


def test_map_error_generic_request_exception_raises_quickml_connection_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    exc = requests.exceptions.RequestException("Generic request error")

    # Act
    mapped = client._map_error(exc)

    # Assert
    assert isinstance(mapped, QuickMLConnectionError)


def test_map_error_http_401_raises_quickml_auth_error(client: QuickMLClient) -> None:
    # Arrange
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized token"

    # Act
    mapped = client._map_error(response=mock_resp)

    # Assert
    assert isinstance(mapped, QuickMLAuthError)
    assert "401" in str(mapped)


def test_map_error_http_403_raises_quickml_auth_error(client: QuickMLClient) -> None:
    # Arrange
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden"

    # Act
    mapped = client._map_error(response=mock_resp)

    # Assert
    assert isinstance(mapped, QuickMLAuthError)
    assert "403" in str(mapped)


def test_map_error_http_429_raises_quickml_rate_limit_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    # Act
    mapped = client._map_error(response=mock_resp)

    # Assert
    assert isinstance(mapped, QuickMLRateLimitError)
    assert "429" in str(mapped)


def test_map_error_http_500_raises_quickml_response_error(
    client: QuickMLClient,
) -> None:
    # Arrange
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    # Act
    mapped = client._map_error(response=mock_resp)

    # Assert
    assert isinstance(mapped, QuickMLResponseError)
    assert "500" in str(mapped)


def test_map_error_unknown_error_raises_quickml_response_error(
    client: QuickMLClient,
) -> None:
    # Act
    mapped = client._map_error()

    # Assert
    assert isinstance(mapped, QuickMLResponseError)
    assert "unknown quickml error" in str(mapped).lower()


# ── Public API Pipeline Tests ─────────────────────────────────────────────────

@patch("requests.post")
def test_generate_executes_full_pipeline(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": "Final synthesized assistant text",
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        "finish_reason": "stop",
    }
    mock_post.return_value = mock_resp

    # Act
    response = client.generate(sample_request)

    # Assert
    assert isinstance(response, LLMResponse)
    assert response.content == "Final synthesized assistant text"
    assert response.usage == UsageMetadata(prompt_tokens=20, completion_tokens=10, total_tokens=30)
    assert response.finish_reason == "stop"


@patch("requests.post")
def test_generate_pipeline_exceptions_propagate(
    mock_post: MagicMock, client: QuickMLClient, sample_request: LLMRequest
) -> None:
    # Arrange
    mock_post.side_effect = requests.exceptions.Timeout("API Request timed out")

    # Act & Assert
    with pytest.raises(QuickMLTimeoutError) as exc_info:
        client.generate(sample_request)

    assert "timed out" in str(exc_info.value).lower()
