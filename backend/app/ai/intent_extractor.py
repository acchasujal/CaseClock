"""backend/app/ai/intent_extractor.py

Application-layer component responsible for converting raw user text into a
validated, fully-typed :class:`Intent` object.

Pipeline
--------
1. Render the intent prompt via :class:`PromptManager`.
2. Load the ``intent_schema.json`` JSON Schema.
3. Build a provider-agnostic :class:`LLMRequest` (temperature=0, no tools).
4. Call :meth:`QuickMLClient.generate` to obtain an :class:`LLMResponse`.
5. Extract the JSON payload from the response content (handles markdown fences).
6. Validate the payload against the JSON Schema using ``jsonschema``.
7. Construct and return a fully-typed :class:`Intent` (with its :class:`Entity`
   list).  Raise :class:`IntentExtractionError` on *any* failure.

Design constraints
------------------
* Never returns a partial intent.
* Never uses regex for JSON extraction.
* No mutable module-level state.
* All prompt strings are sourced exclusively from :class:`PromptManager`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import jsonschema

from backend.app.ai.exceptions import IntentExtractionError, QuickMLError
from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.schemas import ChatMessage, Entity, Intent, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_INTENT_SCHEMA_NAME = "intent_schema"
_JSON_FENCE_START = "```json"
_JSON_FENCE_GENERIC = "```"


# ── IntentExtractor ───────────────────────────────────────────────────────────


class IntentExtractor:
    """Converts a raw user utterance into a validated :class:`Intent`.

    Parameters
    ----------
    client:
        Infrastructure client for QuickML inference.
    prompt_manager:
        Manager for prompt template retrieval and JSON schema loading.

    Raises
    ------
    IntentExtractionError
        Raised if intent extraction fails for any reason:

        * The LLM response is empty.
        * The response cannot be parsed as JSON.
        * The JSON does not conform to ``intent_schema.json``.
        * The QuickML provider signals an error.

    Examples
    --------
    >>> extractor = IntentExtractor(client=client, prompt_manager=pm)
    >>> intent = extractor.extract("Show me repeat offenders in North Zone")
    >>> intent.name
    'GET_REPEAT_OFFENDERS'
    """

    def __init__(
        self,
        client: QuickMLClient,
        prompt_manager: PromptManager,
    ) -> None:
        self._client = client
        self._prompt_manager = prompt_manager

    # ── Public API ─────────────────────────────────────────────────────────────

    def extract(self, user_message: str) -> Intent:
        """Extract a structured :class:`Intent` from a raw user message.

        Parameters
        ----------
        user_message:
            The user's natural-language query string.

        Returns
        -------
        Intent
            Fully validated intent object with entities.

        Raises
        ------
        IntentExtractionError
            On any extraction, parsing, or validation failure.
        """
        if not user_message or not user_message.strip():
            raise IntentExtractionError(
                "Cannot extract intent from an empty user message."
            )

        schema = self._load_schema()
        llm_request = self._build_request(user_message)

        logger.debug(
            "IntentExtractor: dispatching inference for message=%r",
            user_message[:120],
        )

        try:
            llm_response: LLMResponse = self._client.generate(llm_request)
        except QuickMLError:
            # Preserve provider failures so the HTTP route can map them to a
            # controlled 401/429/502/503/504 response instead of a generic 500.
            raise
        except Exception as exc:
            raise IntentExtractionError(
                f"QuickML provider failure during intent extraction: {exc}"
            ) from exc

        raw_payload = self._extract_json(llm_response)
        validated = self._validate_schema(raw_payload, schema)
        return self._build_intent(validated)

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _build_request(self, user_message: str) -> LLMRequest:
        """Render the intent prompt and construct a provider-agnostic LLMRequest.

        The rendered prompt becomes the ``system`` message; the user's raw text
        becomes the ``user`` message.  Temperature is locked to 0.0 to ensure
        deterministic JSON output.
        """
        intent_prompt = self._prompt_manager.get_prompt(PromptType.INTENT)

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=intent_prompt),
            ChatMessage(role="user", content=user_message),
        ]

        return LLMRequest(
            messages=messages,
            temperature=0.0,
            thinking=False,
        )

    def _load_schema(self) -> dict[str, Any]:
        """Load the intent JSON Schema from the PromptManager schema cache.

        Returns
        -------
        dict[str, Any]
            Parsed JSON Schema dictionary.

        Raises
        ------
        IntentExtractionError
            If the schema file is missing or unreadable.
        """
        try:
            return self._prompt_manager.get_schema(_INTENT_SCHEMA_NAME)
        except Exception as exc:
            raise IntentExtractionError(
                f"Failed to load intent JSON Schema '{_INTENT_SCHEMA_NAME}': {exc}"
            ) from exc

    def _extract_json(self, response: LLMResponse) -> dict[str, Any]:
        """Extract a JSON object from the LLM response content.

        Handles two response formats:

        * Plain JSON: ``{"intent": "...", ...}``
        * Markdown-fenced JSON::

            ```json
            {"intent": "...", ...}
            ```

        Never uses regular expressions.  Uses ``json.loads`` on the cleaned
        string after stripping markdown fences.

        Parameters
        ----------
        response:
            Provider-agnostic :class:`LLMResponse` from QuickML.

        Returns
        -------
        dict[str, Any]
            Parsed JSON payload.

        Raises
        ------
        IntentExtractionError
            If the response has no content, or if parsing fails.
        """
        content = response.content
        if not content or not content.strip():
            raise IntentExtractionError(
                "LLM response content is empty; cannot extract intent JSON."
            )

        cleaned = content.strip()

        # Strip markdown fences if present. We do not use regex -- only string
        # operations on well-defined fence delimiters.
        if cleaned.startswith(_JSON_FENCE_START):
            # Remove opening ```json and trailing ```
            cleaned = cleaned[len(_JSON_FENCE_START):]
            if cleaned.endswith(_JSON_FENCE_GENERIC):
                cleaned = cleaned[: -len(_JSON_FENCE_GENERIC)]
            cleaned = cleaned.strip()
        elif cleaned.startswith(_JSON_FENCE_GENERIC):
            # Generic ``` fence without language tag
            cleaned = cleaned[len(_JSON_FENCE_GENERIC):]
            if cleaned.endswith(_JSON_FENCE_GENERIC):
                cleaned = cleaned[: -len(_JSON_FENCE_GENERIC)]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise IntentExtractionError(
                f"LLM response is not valid JSON. "
                f"Parse error at position {exc.pos}: {exc.msg}. "
                f"Raw content: {content[:300]!r}"
            ) from exc

        if not isinstance(parsed, dict):
            raise IntentExtractionError(
                f"LLM response JSON must be a top-level object, "
                f"got {type(parsed).__name__!r}. Content: {content[:300]!r}"
            )

        return parsed

    def _validate_schema(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a parsed JSON dict against the intent JSON Schema.

        Parameters
        ----------
        payload:
            Parsed JSON payload from the LLM response.
        schema:
            Loaded JSON Schema dictionary.

        Returns
        -------
        dict[str, Any]
            The same payload, returned for chaining.

        Raises
        ------
        IntentExtractionError
            If validation fails, carrying the validation error message.
        """
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as exc:
            raise IntentExtractionError(
                f"Intent JSON failed schema validation: {exc.message} "
                f"(path: {' -> '.join(str(p) for p in exc.absolute_path)})"
            ) from exc
        except jsonschema.SchemaError as exc:
            raise IntentExtractionError(
                f"Intent JSON Schema itself is malformed: {exc.message}"
            ) from exc

        return payload

    def _parse_entities(self, raw_entities: list[dict[str, Any]]) -> list[Entity]:
        """Convert validated raw entity dicts into :class:`Entity` models.

        Parameters
        ----------
        raw_entities:
            List of raw entity dictionaries (already schema-validated).

        Returns
        -------
        list[Entity]
            Typed entity list.  Entities missing optional fields are still
            accepted (the schema enforces only ``type`` and ``value``).
        """
        entities: list[Entity] = []
        for raw in raw_entities:
            try:
                entities.append(
                    Entity(
                        type=str(raw["type"]),
                        value=raw["value"],
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                # Schema validation already guarantees structure; this is a
                # defensive belt-and-suspenders guard.
                raise IntentExtractionError(
                    f"Failed to construct Entity from validated payload: {exc}. "
                    f"Raw entity: {raw!r}"
                ) from exc

        return entities

    def _build_intent(self, validated: dict[str, Any]) -> Intent:
        """Construct a fully-typed :class:`Intent` from a validated payload dict.

        Parameters
        ----------
        validated:
            Schema-validated JSON dictionary containing at minimum
            ``intent`` and ``entities`` keys.

        Returns
        -------
        Intent
            Fully typed intent model.

        Raises
        ------
        IntentExtractionError
            If Intent construction fails for any reason.
        """
        try:
            entities = self._parse_entities(
                validated.get("entities") or []
            )
            confidence_raw = validated.get("confidence")
            confidence: float | None = (
                float(confidence_raw)
                if confidence_raw is not None
                else None
            )
            return Intent(
                name=str(validated["intent"]),
                confidence=confidence,
                entities=entities,
            )
        except IntentExtractionError:
            raise
        except Exception as exc:
            raise IntentExtractionError(
                f"Failed to construct Intent model from validated payload: {exc}"
            ) from exc
