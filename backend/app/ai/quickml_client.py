"""backend/app/ai/quickml_client.py

Infrastructure client for communicating with Zoho Catalyst QuickML REST API.
Converts provider-agnostic LLMRequest into QuickML payload and maps responses
to provider-agnostic LLMResponse. Reuses existing CatalystRestDatastore OAuth.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from backend.app.ai.exceptions import (
    QuickMLAuthError,
    QuickMLConfigurationError,
    QuickMLConnectionError,
    QuickMLRateLimitError,
    QuickMLResponseError,
    QuickMLTimeoutError,
)
from backend.app.ai.schemas import (
    LLMRequest,
    LLMResponse,
    ToolCall,
    UsageMetadata,
)
from backend.app.db.catalyst import CatalystRestDatastore

PROTECTED_PAYLOAD_KEYS = {
    "model",
    "messages",
    "temperature",
    "max_tokens",
    "tools",
    "response_format",
    "chat_template_kwargs",
    "stream",
}

class QuickMLClient:
    """Infrastructure client responsible for direct HTTP interaction with Catalyst QuickML API."""

    def __init__(
        self,
        datastore: CatalystRestDatastore,
        default_model: str = "crm-di-glm47b_30b_it",
        timeout: int | float | None = None,
        org_id: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        """Initialize QuickMLClient using existing CatalystRestDatastore.
        
        Args:
            datastore: Initialized CatalystRestDatastore for OAuth token retrieval and domain options.
            default_model: Fallback LLM model identifier.
            timeout: Optional HTTP request timeout in seconds.
            org_id: Optional Catalyst Org ID header value. Defaults to env CATALYST_ORG or CATALYST_ORG_ID.
        """
        self._datastore = datastore
        self._default_model = default_model
        self._timeout = timeout or getattr(datastore, "timeout", 30)
        self._org_id = (
            org_id
            or os.getenv("QUICKML_ORG_ID")
            or os.getenv("CATALYST_ORG")
            or os.getenv("CATALYST_ORG_ID")
            or ""
        )
        self._endpoint = (endpoint or os.getenv("QUICKML_ENDPOINT") or "").rstrip("/")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Sends an inference request to Catalyst QuickML and returns a provider-agnostic response.
        
        Args:
            request: Provider-agnostic LLM request payload.
            
        Returns:
            Provider-agnostic LLM response payload.
            
        Raises:
            QuickMLAuthError: If authentication fails.
            QuickMLTimeoutError: If the request times out.
            QuickMLConnectionError: If network connection fails.
            QuickMLRateLimitError: If API rate limit (HTTP 429) is hit.
            QuickMLResponseError: If the API returns a non-200 HTTP response or unparseable payload.
        """
        payload = self._build_payload(request)
        headers = self._build_headers()
        try:
            raw_resp = self._send_request(headers, payload)
        except QuickMLAuthError:
            # Access tokens are short-lived. Refresh once after a provider 401,
            # then surface the controlled provider error if it still fails.
            invalidate = getattr(self._datastore, "invalidate_access_token", None)
            if callable(invalidate):
                invalidate()
                raw_resp = self._send_request(self._build_headers(), payload)
            else:
                raise
        return self._parse_response(raw_resp)

    def _build_headers(self) -> dict[str, str]:
        """Constructs required HTTP headers including OAuth token and CATALYST-ORG."""
        try:
            token = self._datastore.access_token()
        except ValueError as exc:
            raise QuickMLConfigurationError(str(exc)) from exc
        except Exception as exc:
            raise QuickMLAuthError("Failed to acquire Catalyst OAuth access token.") from exc

        if not token:
            raise QuickMLAuthError("Catalyst OAuth provider returned an empty access token.")

        if not self._org_id:
            raise QuickMLAuthError("Missing CATALYST-ORG identifier in configuration or environment.")

        return {
            "Authorization": f"Zoho-oauthtoken {token}",
            "CATALYST-ORG": self._org_id,
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        """Translates provider-agnostic LLMRequest into QuickML API payload format."""
        messages_payload: list[dict[str, Any]] = []
        for msg in request.messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            messages_payload.append(item)

        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": messages_payload,
            "temperature": request.temperature,
            "stream": False,
            "chat_template_kwargs": {
                "enable_thinking": request.thinking
            },
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.tools:
            payload["tools"] = request.tools

        if request.response_format:
            payload["response_format"] = request.response_format

        if request.extra_kwargs:
            for key, value in request.extra_kwargs.items():
                if key not in PROTECTED_PAYLOAD_KEYS:
                    payload[key] = value

        return payload

    def _send_request(self, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        """Executes POST request against QuickML chat endpoint with error handling."""
        url = self._endpoint
        if not url:
            api_domain = str(getattr(self._datastore, "api_domain", "https://api.catalyst.zoho.in")).rstrip("/")
            project_id = str(getattr(self._datastore, "project_id", ""))
            url = f"{api_domain}/quickml/v1/project/{project_id}/glm/chat"

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise self._map_error(exc) from exc

        if response.status_code not in (200, 201):
            raise self._map_error(response=response)

        try:
            return response.json()
        except Exception as exc:
            raise QuickMLResponseError(
                message="Failed to parse QuickML JSON response.",
                status_code=response.status_code,
                response_body=None,
            ) from exc

    def _parse_response(self, raw_resp: dict[str, Any]) -> LLMResponse:
        """Parses QuickML API JSON output into provider-agnostic LLMResponse."""
        content: str | None = None
        if "response" in raw_resp and isinstance(raw_resp["response"], str):
            content = raw_resp["response"]
        elif "choices" in raw_resp and isinstance(raw_resp["choices"], list) and raw_resp["choices"]:
            choice = raw_resp["choices"][0]
            if isinstance(choice, dict):
                msg = choice.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    content = msg["content"]

        # Parse tool calls (supporting both top-level and choices[0].message.tool_calls)
        tool_calls: list[ToolCall] = []
        raw_tools = raw_resp.get("tool_calls")
        if not raw_tools and "choices" in raw_resp and isinstance(raw_resp["choices"], list) and raw_resp["choices"]:
            choice = raw_resp["choices"][0]
            if isinstance(choice, dict):
                msg = choice.get("message")
                if isinstance(msg, dict):
                    raw_tools = msg.get("tool_calls")

        if isinstance(raw_tools, list):
            for tc in raw_tools:
                if isinstance(tc, dict):
                    name = str(tc.get("name") or tc.get("function", {}).get("name") or "")
                    args = tc.get("arguments") or tc.get("function", {}).get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"raw": args}
                    call_id = tc.get("id") or tc.get("call_id")
                    if name:
                        tool_calls.append(ToolCall(name=name, arguments=args, call_id=call_id))

        # Fail fast if response does not contain text content or tool calls
        if content is None and not tool_calls:
            raise QuickMLResponseError(
                message="QuickML response payload missing both 'response' text and 'choices[0].message.content'.",
                response_body=json.dumps(raw_resp),
            )

        # Parse usage metadata
        usage: UsageMetadata | None = None
        raw_usage = raw_resp.get("usage")
        if isinstance(raw_usage, dict):
            usage = UsageMetadata(
                prompt_tokens=int(raw_usage.get("prompt_tokens") or 0),
                completion_tokens=int(raw_usage.get("completion_tokens") or 0),
                total_tokens=int(raw_usage.get("total_tokens") or 0),
            )

        # Parse finish_reason (do not invent provider default values)
        finish_reason: str | None = None
        if "finish_reason" in raw_resp and raw_resp["finish_reason"] is not None:
            finish_reason = str(raw_resp["finish_reason"])
        elif "choices" in raw_resp and isinstance(raw_resp["choices"], list) and raw_resp["choices"]:
            choice = raw_resp["choices"][0]
            if isinstance(choice, dict) and choice.get("finish_reason") is not None:
                finish_reason = str(choice["finish_reason"])

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
            raw_metadata=raw_resp,
        )

    def _map_error(
        self,
        exc: Exception | None = None,
        response: requests.Response | None = None,
    ) -> Exception:
        """Maps HTTP errors and network exceptions to QuickML domain exceptions."""
        if exc is not None:
            if isinstance(exc, requests.exceptions.Timeout):
                return QuickMLTimeoutError(f"QuickML request timed out: {exc}")
            if isinstance(exc, (requests.exceptions.SSLError, requests.exceptions.ConnectionError)):
                return QuickMLConnectionError(f"QuickML network connection failed: {exc}")
            if isinstance(exc, requests.exceptions.RequestException):
                return QuickMLConnectionError(f"QuickML request failed: {exc}")
            return QuickMLResponseError(f"Unexpected QuickML error: {exc}")

        if response is not None:
            status_code = response.status_code
            # Provider responses can contain sensitive diagnostic material.
            # Keep only the status/category in exception text.
            if status_code in (401, 403):
                return QuickMLAuthError(
                    f"QuickML authentication failed (HTTP {status_code})."
                )
            if status_code == 429:
                return QuickMLRateLimitError(
                    "QuickML API rate limit exceeded (HTTP 429)."
                )
            return QuickMLResponseError(
                message=f"QuickML API returned HTTP {status_code}.",
                status_code=status_code,
                response_body=None,
            )

        return QuickMLResponseError("Unknown QuickML error occurred.")
