"""tests/ai/test_intent_dispatcher.py

Comprehensive unit tests for backend.app.ai.intent_dispatcher.IntentDispatcher.
Verifies helper functions, registry immutability, exception handling, intent routing,
and deterministic graph service handler execution.
"""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import MagicMock

import pytest

from backend.app.ai.exceptions import ToolExecutionError
from backend.app.ai.intent_dispatcher import (
    IntentDispatcher,
    IntentName,
    _first_entity_value,
    _require_entity,
)
from backend.app.ai.schemas import Entity, Intent
from backend.app.core.graph.services.graph_service import GraphService
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.network_service import NetworkService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.core.graph.services.similarity_service import SimilarityService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_services() -> dict[str, MagicMock]:
    return {
        "graph_service": MagicMock(spec=GraphService),
        "hotspot_service": MagicMock(spec=HotspotService),
        "network_service": MagicMock(spec=NetworkService),
        "offender_service": MagicMock(spec=OffenderService),
        "similarity_service": MagicMock(spec=SimilarityService),
    }


@pytest.fixture
def dispatcher(mock_services: dict[str, MagicMock]) -> IntentDispatcher:
    return IntentDispatcher(
        graph_service=mock_services["graph_service"],
        hotspot_service=mock_services["hotspot_service"],
        network_service=mock_services["network_service"],
        offender_service=mock_services["offender_service"],
        similarity_service=mock_services["similarity_service"],
    )


# ── Helper Function Tests ─────────────────────────────────────────────────────

def test_first_entity_value_returns_first_matching_entity() -> None:
    # Arrange
    entities = [
        Entity(type="case_id", value="CR-2026-001"),
        Entity(type="case_id", value="CR-2026-002"),
    ]

    # Act
    result = _first_entity_value(entities, "case_id")

    # Assert
    assert result == "CR-2026-001"


def test_first_entity_value_returns_none_if_absent() -> None:
    # Arrange
    entities = [Entity(type="officer_id", value="officer-99")]

    # Act
    result = _first_entity_value(entities, "case_id")

    # Assert
    assert result is None


def test_first_entity_value_ignores_unrelated_entities() -> None:
    # Arrange
    entities = [
        Entity(type="zone", value="North"),
        Entity(type="case_id", value="CR-2026-100"),
    ]

    # Act
    result = _first_entity_value(entities, "case_id")

    # Assert
    assert result == "CR-2026-100"


def test_require_entity_returns_required_entity_value() -> None:
    # Arrange
    intent = Intent(
        name="GET_CASE",
        entities=[Entity(type="case_id", value="CR-2026-777")],
    )

    # Act
    value = _require_entity(intent, "case_id")

    # Assert
    assert value == "CR-2026-777"


def test_require_entity_missing_entity_raises_tool_execution_error() -> None:
    # Arrange
    intent = Intent(name="GET_CASE", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError):
        _require_entity(intent, "case_id")


def test_require_entity_error_message_contains_intent_name() -> None:
    # Arrange
    intent = Intent(name="GET_CLOCK", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        _require_entity(intent, "case_id")

    assert "GET_CLOCK" in str(exc_info.value)


def test_require_entity_error_message_contains_missing_entity_type() -> None:
    # Arrange
    intent = Intent(name="GET_DEPENDENCIES", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        _require_entity(intent, "case_id")

    assert "case_id" in str(exc_info.value)


# ── Registry Tests ────────────────────────────────────────────────────────────

def test_registry_contains_every_intent_name(dispatcher: IntentDispatcher) -> None:
    # Act
    registry_keys = set(dispatcher._registry.keys())

    # Assert
    assert registry_keys == set(IntentName)


def test_registry_is_mapping_proxy_type(dispatcher: IntentDispatcher) -> None:
    # Assert
    assert isinstance(dispatcher._registry, MappingProxyType)


def test_modifying_registry_raises_type_error(dispatcher: IntentDispatcher) -> None:
    # Act & Assert
    with pytest.raises(TypeError):
        dispatcher._registry[IntentName.GET_CASE] = None  # type: ignore[index]


# ── Dispatch Tests ────────────────────────────────────────────────────────────

def test_dispatch_unknown_intent_raises_tool_execution_error(
    dispatcher: IntentDispatcher,
) -> None:
    # Arrange
    intent = Intent(name="UNREGISTERED_INTENT", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch(intent)

    assert "UNREGISTERED_INTENT" in str(exc_info.value)


def test_dispatch_registered_handler_executes_correctly(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    mock_services["hotspot_service"].get_all_hotspots.return_value = {"summary": "ok"}
    intent = Intent(name="GET_HOTSPOTS", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"summary": "ok"}
    mock_services["hotspot_service"].get_all_hotspots.assert_called_once()


def test_dispatch_propagates_tool_execution_error_unchanged(
    dispatcher: IntentDispatcher,
) -> None:
    # Arrange
    intent = Intent(name="GET_CASE", entities=[])  # missing required 'case_id'

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch(intent)

    assert "requires entity type 'case_id'" in str(exc_info.value)


def test_dispatch_wraps_unexpected_service_exception(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    mock_services["offender_service"].get_repeat_offenders.side_effect = RuntimeError("Database crash")
    intent = Intent(name="GET_REPEAT_OFFENDERS", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch(intent)

    assert "execution failed" in str(exc_info.value).lower()
    assert exc_info.value.__cause__ is not None


def test_dispatch_logging_does_not_affect_behavior(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    mock_services["hotspot_service"].get_all_hotspots.return_value = {"report": "active"}
    intent = Intent(name="GET_HOTSPOTS", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"report": "active"}


# ── Handler Specific Tests ───────────────────────────────────────────────────

def test_handle_get_case_calls_network_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    mock_services["network_service"].get_case.return_value = {"case": {"id": "CR-101"}}
    intent = Intent(name="GET_CASE", entities=[Entity(type="case_id", value="CR-101")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"case": {"id": "CR-101"}}
    mock_services["network_service"].get_case.assert_called_once_with("CR-101")


def test_handle_get_case_details_aggregates_case_accused_and_sections(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    ns = mock_services["network_service"]
    ns.get_case.return_value = {"case": {"id": "CR-200"}}
    ns.get_co_accused.return_value = {"accused": [{"id": "p1"}], "accused_count": 1}
    ns.get_sections_for_case.return_value = {"sections": [{"id": "s302"}], "section_count": 1}
    intent = Intent(name="GET_CASE_DETAILS", entities=[Entity(type="case_id", value="CR-200")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result["case_id"] == "CR-200"
    assert result["case"] == {"id": "CR-200"}
    assert len(result["accused"]) == 1
    assert len(result["sections"]) == 1
    ns.get_case.assert_called_once_with("CR-200")
    ns.get_co_accused.assert_called_once_with("CR-200")
    ns.get_sections_for_case.assert_called_once_with("CR-200")


def test_handle_get_case_details_returns_immediately_on_case_error(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    ns = mock_services["network_service"]
    ns.get_case.return_value = {"error": "Case not found", "case_id": "CR-404"}
    intent = Intent(name="GET_CASE_DETAILS", entities=[Entity(type="case_id", value="CR-404")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"error": "Case not found", "case_id": "CR-404"}
    ns.get_case.assert_called_once_with("CR-404")
    ns.get_co_accused.assert_not_called()
    ns.get_sections_for_case.assert_not_called()


def test_handle_get_similar_cases_calls_similarity_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    ss = mock_services["similarity_service"]
    ss.get_similar_cases.return_value = {"matches": []}
    intent = Intent(name="GET_SIMILAR_CASES", entities=[Entity(type="case_id", value="CR-500")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"matches": []}
    ss.get_similar_cases.assert_called_once_with("CR-500")


def test_handle_get_repeat_offenders_calls_offender_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    os_ = mock_services["offender_service"]
    os_.get_repeat_offenders.return_value = {"offenders": []}
    intent = Intent(name="GET_REPEAT_OFFENDERS", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"offenders": []}
    os_.get_repeat_offenders.assert_called_once_with()


def test_handle_get_network_with_case_id_calls_case_network(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    gs = mock_services["graph_service"]
    gs.get_case_network.return_value = {"nodes": [], "edges": []}
    intent = Intent(name="GET_NETWORK", entities=[Entity(type="case_id", value="CR-999")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"nodes": [], "edges": []}
    gs.get_case_network.assert_called_once_with("CR-999")
    gs.get_person_network.assert_not_called()


def test_handle_get_network_with_officer_id_calls_person_network(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    gs = mock_services["graph_service"]
    gs.get_person_network.return_value = {"nodes": [], "edges": []}
    intent = Intent(name="GET_NETWORK", entities=[Entity(type="officer_id", value="officer-7")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"nodes": [], "edges": []}
    gs.get_person_network.assert_called_once_with("officer-7")
    gs.get_case_network.assert_not_called()


def test_handle_get_network_missing_both_entities_raises_tool_execution_error(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    intent = Intent(name="GET_NETWORK", entities=[])

    # Act & Assert
    with pytest.raises(ToolExecutionError) as exc_info:
        dispatcher.dispatch(intent)

    assert "requires at least one entity" in str(exc_info.value).lower()


def test_handle_get_hotspots_calls_hotspot_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    hs = mock_services["hotspot_service"]
    hs.get_all_hotspots.return_value = {"temporal": {}}
    intent = Intent(name="GET_HOTSPOTS", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"temporal": {}}
    hs.get_all_hotspots.assert_called_once_with()


def test_handle_get_dependencies_calls_network_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    ns = mock_services["network_service"]
    ns.get_dependency_chain.return_value = {"dependencies": []}
    intent = Intent(name="GET_DEPENDENCIES", entities=[Entity(type="case_id", value="CR-777")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"dependencies": []}
    ns.get_dependency_chain.assert_called_once_with("CR-777")


def test_handle_get_clock_calls_network_service(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    ns = mock_services["network_service"]
    ns.get_clock_instances.return_value = {"clocks": []}
    intent = Intent(name="GET_CLOCK", entities=[Entity(type="case_id", value="CR-777")])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result == {"clocks": []}
    ns.get_clock_instances.assert_called_once_with("CR-777")


def test_handle_general_chat_bypasses_graph_services(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    intent = Intent(name="GENERAL_CHAT", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result["intent"] == "GENERAL_CHAT"
    assert result["graph_data"] is None
    for service_mock in mock_services.values():
        service_mock.assert_not_called()


def test_handle_unknown_bypasses_graph_services(
    dispatcher: IntentDispatcher,
    mock_services: dict[str, MagicMock],
) -> None:
    # Arrange
    intent = Intent(name="UNKNOWN", entities=[])

    # Act
    result = dispatcher.dispatch(intent)

    # Assert
    assert result["intent"] == "UNKNOWN"
    assert result["graph_data"] is None
    for service_mock in mock_services.values():
        service_mock.assert_not_called()
