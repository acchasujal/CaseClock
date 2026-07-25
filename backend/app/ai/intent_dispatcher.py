"""backend/app/ai/intent_dispatcher.py

Application-layer orchestrator that maps a validated :class:`Intent` to its
corresponding deterministic graph service call.

Architecture
------------
This module sits at the boundary between the AI layer (intent extraction) and
the domain graph layer (deterministic services).  It enforces the following
invariants:

* **No AI logic.**  No inference, scoring, or probabilistic decisions live here.
* **No domain knowledge.**  The dispatcher does not know *what* a case is; it
  only knows *which service method* handles a given intent name.
* **Registry pattern.**  Intent-to-handler mappings are expressed as a single
  ``dict[str, _HandlerFn]``, not as ``if/elif`` chains.
* **Dependency injection.**  All graph services are injected at construction
  time; the dispatcher is agnostic to their implementations.
* **Single responsibility.**  Each handler is a minimal lambda or method that
  extracts entity parameters from the :class:`Intent` and calls one service
  method.

Intent → Service mapping
-------------------------
+----------------------+---------------------+------------------------------+
| Intent name          | Service             | Primary method               |
+======================+=====================+==============================+
| GET_CASE             | NetworkService      | get_case(case_id)            |
+----------------------+---------------------+------------------------------+
| GET_CASE_DETAILS     | NetworkService      | get_case(case_id)            |
+----------------------+---------------------+------------------------------+
| GET_SIMILAR_CASES    | SimilarityService   | get_similar_cases(case_id)   |
+----------------------+---------------------+------------------------------+
| GET_REPEAT_OFFENDERS | OffenderService     | get_repeat_offenders()       |
+----------------------+---------------------+------------------------------+
| GET_NETWORK          | GraphService        | get_case_network(case_id)    |
+----------------------+---------------------+------------------------------+
| GET_HOTSPOTS         | HotspotService      | get_all_hotspots()           |
+----------------------+---------------------+------------------------------+
| GET_DEPENDENCIES     | NetworkService      | get_dependency_chain(case_id)|
+----------------------+---------------------+------------------------------+
| GET_CLOCK            | NetworkService      | get_clock_instances(case_id) |
+----------------------+---------------------+------------------------------+
| GENERAL_CHAT         | —                   | pass-through                 |
+----------------------+---------------------+------------------------------+
| UNKNOWN              | —                   | pass-through                 |
+----------------------+---------------------+------------------------------+
"""

from __future__ import annotations

import logging
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable

from backend.app.ai.exceptions import ToolExecutionError
from backend.app.ai.schemas import Entity, Intent
from backend.app.core.graph.services.graph_service import GraphService
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.network_service import NetworkService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.core.graph.services.similarity_service import SimilarityService

logger = logging.getLogger(__name__)

# ── Type alias for a registered handler ───────────────────────────────────────

# Each handler receives the intent and returns a JSON-serializable dict.
_HandlerFn = Callable[[Intent], dict[str, Any]]


# ── Intent name enumeration (single authoritative registry) ──────────────────


class IntentName(str, Enum):
    """Enumeration of all valid intent names supported by the dispatcher.

    Inherits from ``str`` so that members compare equal to their string
    counterparts and can be used directly as ``dict`` keys or in
    ``jsonschema``-validated payloads without calling ``.value``.

    Use these members everywhere in place of bare string literals so that
    intent names are defined exactly once and benefit from IDE autocomplete
    and static type checking.
    """

    GET_CASE = "GET_CASE"
    GET_CASE_DETAILS = "GET_CASE_DETAILS"
    GET_SIMILAR_CASES = "GET_SIMILAR_CASES"
    GET_REPEAT_OFFENDERS = "GET_REPEAT_OFFENDERS"
    GET_NETWORK = "GET_NETWORK"
    GET_HOTSPOTS = "GET_HOTSPOTS"
    GET_DEPENDENCIES = "GET_DEPENDENCIES"
    GET_CLOCK = "GET_CLOCK"
    GENERAL_CHAT = "GENERAL_CHAT"
    UNKNOWN = "UNKNOWN"


# ── Entity extraction helpers ─────────────────────────────────────────────────


def _first_entity_value(entities: list[Entity], entity_type: str) -> str | None:
    """Return the value of the first entity matching *entity_type*, or ``None``.

    Parameters
    ----------
    entities:
        List of entities extracted by the intent extractor.
    entity_type:
        The ``Entity.type`` string to match (e.g. ``"case_id"``).

    Returns
    -------
    str | None
        The string value of the first match, or ``None`` if not found.
    """
    for entity in entities:
        if entity.type == entity_type:
            return str(entity.value)
    return None


def _require_entity(intent: Intent, entity_type: str) -> str:
    """Extract a required entity value, raising :class:`ToolExecutionError` if absent.

    Parameters
    ----------
    intent:
        The validated :class:`Intent` containing entities.
    entity_type:
        The required entity type key (e.g. ``"case_id"``).

    Returns
    -------
    str
        The extracted entity value as a string.

    Raises
    ------
    ToolExecutionError
        If no entity of the requested type is present in the intent.
    """
    value = _first_entity_value(intent.entities, entity_type)
    if value is None:
        raise ToolExecutionError(
            f"Intent '{intent.name}' requires entity type '{entity_type}', "
            f"but none was found in: {[e.type for e in intent.entities]}",
            tool_name=intent.name,
        )
    return value


# ── IntentDispatcher ──────────────────────────────────────────────────────────


class IntentDispatcher:
    """Maps a validated :class:`Intent` to a deterministic graph service call.

    All graph services are injected at construction time.  The dispatcher builds
    an internal registry ``dict[str, _HandlerFn]`` once and reuses it across
    calls; there is no mutable state after initialization.

    Parameters
    ----------
    graph_service:
        Service for network traversal, aggregation, and statistics.
    hotspot_service:
        Service for hotspot pattern detection.
    network_service:
        Service for single-node lookups, case traversals, clock, and
        dependency chains.
    offender_service:
        Service for repeat offender intelligence.
    similarity_service:
        Service for case similarity search.

    Examples
    --------
    >>> dispatcher = IntentDispatcher(
    ...     graph_service=gs,
    ...     hotspot_service=hs,
    ...     network_service=ns,
    ...     offender_service=os_,
    ...     similarity_service=ss,
    ... )
    >>> result = dispatcher.dispatch(intent)
    """

    def __init__(
        self,
        graph_service: GraphService,
        hotspot_service: HotspotService,
        network_service: NetworkService,
        offender_service: OffenderService,
        similarity_service: SimilarityService,
    ) -> None:
        self._graph_service = graph_service
        self._hotspot_service = hotspot_service
        self._network_service = network_service
        self._offender_service = offender_service
        self._similarity_service = similarity_service

        # Build the registry once at construction time and wrap it in a
        # MappingProxyType so it cannot be mutated by any caller or subclass.
        self._registry: MappingProxyType[IntentName, _HandlerFn] = (
            MappingProxyType(self._build_registry())
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def dispatch(self, intent: Intent) -> dict[str, Any]:
        """Route an intent to its registered graph service handler.

        Parameters
        ----------
        intent:
            A fully validated :class:`Intent` produced by :class:`IntentExtractor`.

        Returns
        -------
        dict[str, Any]
            JSON-serializable result from the matched graph service.

        Raises
        ------
        ToolExecutionError
            * If the intent name is not registered.
            * If a required entity (e.g. ``case_id``) is missing.
            * If the underlying service call raises an unexpected exception.
        """
        # IntentName is a str Enum; dict lookup works with a plain str key
        # because str.__eq__ is inherited, so intent.name (str) matches enum
        # members when MappingProxyType uses them as keys.
        try:
            intent_key = IntentName(intent.name)
        except ValueError:
            raise ToolExecutionError(
                f"No handler registered for intent '{intent.name}'. "
                f"Valid intents: {[m.value for m in IntentName]}",
                tool_name=intent.name,
            )

        handler = self._registry.get(intent_key)

        if handler is None:
            # Defensive: should never occur after the ValueError guard above.
            raise ToolExecutionError(
                f"Registry lookup returned no handler for intent '{intent.name}'.",
                tool_name=intent.name,
            )

        logger.info(
            "IntentDispatcher: routing intent=%r with entities=%r",
            intent.name,
            [(e.type, e.value) for e in intent.entities],
        )

        try:
            return handler(intent)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(
                f"Graph service execution failed for intent '{intent.name}': {exc}",
                tool_name=intent.name,
            ) from exc

    # ── Registry Builder ───────────────────────────────────────────────────────

    def _build_registry(self) -> dict[IntentName, _HandlerFn]:
        """Construct the intent-name to handler function mapping.

        Returns a plain ``dict`` that ``__init__`` immediately wraps in a
        ``MappingProxyType``; this method itself must not be called after
        construction.  Adding a new intent requires exactly one new entry here.

        Returns:
            A dict mapping every :class:`IntentName` member to its bound
            handler method.  All ten canonical intents must be present.
        """
        return {
            IntentName.GET_CASE: self._handle_get_case,
            IntentName.GET_CASE_DETAILS: self._handle_get_case_details,
            IntentName.GET_SIMILAR_CASES: self._handle_get_similar_cases,
            IntentName.GET_REPEAT_OFFENDERS: self._handle_get_repeat_offenders,
            IntentName.GET_NETWORK: self._handle_get_network,
            IntentName.GET_HOTSPOTS: self._handle_get_hotspots,
            IntentName.GET_DEPENDENCIES: self._handle_get_dependencies,
            IntentName.GET_CLOCK: self._handle_get_clock,
            IntentName.GENERAL_CHAT: self._handle_general_chat,
            IntentName.UNKNOWN: self._handle_unknown,
        }

    # ── Individual Handlers ────────────────────────────────────────────────────

    def _handle_get_case(self, intent: Intent) -> dict[str, Any]:
        """Look up a single case node by its case_id entity.

        Delegates to :meth:`NetworkService.get_case`.

        Required entities
        -----------------
        ``case_id`` — the case identifier (e.g. ``"CR-2026-104"``).
        """
        case_id = _require_entity(intent, "case_id")
        return self._network_service.get_case(case_id)

    def _handle_get_case_details(self, intent: Intent) -> dict[str, Any]:
        """Return full case detail: node, accused persons, and section charges.

        Composes :meth:`NetworkService.get_case`, :meth:`NetworkService.get_co_accused`,
        and :meth:`NetworkService.get_sections_for_case` into a single result dict.

        Required entities
        -----------------
        ``case_id`` — the case identifier.
        """
        case_id = _require_entity(intent, "case_id")
        case_result = self._network_service.get_case(case_id)

        if "error" in case_result:
            # Propagate not-found immediately; do not attempt further lookups.
            return case_result

        accused_result = self._network_service.get_co_accused(case_id)
        sections_result = self._network_service.get_sections_for_case(case_id)

        return {
            "case_id": case_id,
            "case": case_result.get("case"),
            "accused": accused_result.get("accused", []),
            "accused_count": accused_result.get("accused_count", 0),
            "sections": sections_result.get("sections", []),
            "section_count": sections_result.get("section_count", 0),
        }

    def _handle_get_similar_cases(self, intent: Intent) -> dict[str, Any]:
        """Find cases similar to a given case.

        Delegates to :meth:`SimilarityService.get_similar_cases`.

        Required entities
        -----------------
        ``case_id`` — the reference case identifier.
        """
        case_id = _require_entity(intent, "case_id")
        return self._similarity_service.get_similar_cases(case_id)

    def _handle_get_repeat_offenders(self, intent: Intent) -> dict[str, Any]:
        """List repeat offenders with case histories.

        Delegates to :meth:`OffenderService.get_repeat_offenders`.
        No entities required (returns system-wide results).
        """
        return self._offender_service.get_repeat_offenders()

    def _handle_get_network(self, intent: Intent) -> dict[str, Any]:
        """Return the case or person subgraph for visualization.

        Prefers ``case_id`` if present; falls back to ``officer_id`` as a
        person identifier.  Delegates to :meth:`GraphService.get_case_network`
        or :meth:`GraphService.get_person_network`.

        Required entities
        -----------------
        At least one of: ``case_id`` or ``officer_id``.
        """
        case_id = _first_entity_value(intent.entities, "case_id")
        if case_id:
            return self._graph_service.get_case_network(case_id)

        person_id = _first_entity_value(intent.entities, "officer_id")
        if person_id:
            return self._graph_service.get_person_network(person_id)

        raise ToolExecutionError(
            f"Intent '{intent.name}' requires at least one entity of type "
            f"'case_id' or 'officer_id' to resolve a network subgraph.",
            tool_name=intent.name,
        )

    def _handle_get_hotspots(self, intent: Intent) -> dict[str, Any]:
        """Return the full hotspot report (temporal, spatial, workload, network).

        Delegates to :meth:`HotspotService.get_all_hotspots`.
        No entities required (returns system-wide results).
        """
        return self._hotspot_service.get_all_hotspots()

    def _handle_get_dependencies(self, intent: Intent) -> dict[str, Any]:
        """Return all investigation dependency blockers for a case.

        Delegates to :meth:`NetworkService.get_dependency_chain`.

        Required entities
        -----------------
        ``case_id`` — the case identifier.
        """
        case_id = _require_entity(intent, "case_id")
        return self._network_service.get_dependency_chain(case_id)

    def _handle_get_clock(self, intent: Intent) -> dict[str, Any]:
        """Return all statutory clock instances (BNS deadlines) for a case.

        Delegates to :meth:`NetworkService.get_clock_instances`.

        Required entities
        -----------------
        ``case_id`` — the case identifier.
        """
        case_id = _require_entity(intent, "case_id")
        return self._network_service.get_clock_instances(case_id)

    def _handle_general_chat(self, intent: Intent) -> dict[str, Any]:
        """Pass-through handler for conversational or general assistance intents.

        No graph service call is made.  Returns a structured signal for the
        synthesis layer indicating that natural-language fallback is appropriate.
        """
        return {
            "intent": IntentName.GENERAL_CHAT.value,
            "graph_data": None,
            "message": "General conversational query — no graph execution performed.",
        }

    def _handle_unknown(self, intent: Intent) -> dict[str, Any]:
        """Pass-through handler for queries that could not be mapped to an intent.

        No graph service call is made.  Returns a structured signal so that the
        synthesis layer can formulate an appropriate fallback response.
        """
        return {
            "intent": IntentName.UNKNOWN.value,
            "graph_data": None,
            "message": "Query could not be mapped to a known investigative intent.",
        }
