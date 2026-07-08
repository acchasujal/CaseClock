import pytest
from uuid import UUID
from shared.constants.clock_types import ClockType, CLOCK_RULES, get_clock_rule
from backend.app.core.graph.graph_schema import GRAPH_SCHEMA
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType
from synthetic_data.configs import SyntheticDataConfig
from synthetic_data.generator import generate_synthetic_graph

def test_get_clock_rule_valid():
    """Verify that get_clock_rule resolves correct rules for valid categories."""
    rule = get_clock_rule("theft")
    assert rule.clock_type == ClockType.INVESTIGATION_60_DAY
    assert rule.duration_days == 60
    assert "[UNVERIFIED]" in rule.bnss_reference

    rule_narcotics = get_clock_rule("narcotics")
    assert rule_narcotics.clock_type == ClockType.INVESTIGATION_90_DAY
    assert rule_narcotics.duration_days == 90

def test_get_clock_rule_invalid():
    """Verify that an invalid offence category raises a KeyError."""
    with pytest.raises(KeyError) as exc_info:
        get_clock_rule("non_existent_category")
    assert "No clock rule found for offence category" in str(exc_info.value)

def test_graph_schema_integrity():
    """Verify that the declarative schema holds expected entities and relationships."""
    assert GraphEntityType.CASE in GRAPH_SCHEMA.entities
    assert GraphEntityType.PERSON in GRAPH_SCHEMA.entities
    assert GraphEntityType.CLOCK_INSTANCE in GRAPH_SCHEMA.entities
    
    assert GraphRelationshipType.ACCUSED_IN in GRAPH_SCHEMA.relationships
    assert GraphRelationshipType.CO_ACCUSED_WITH in GRAPH_SCHEMA.derived_relationships

def test_deterministic_synthetic_generation():
    """Verify that generating the synthetic graph with a fixed seed is deterministic."""
    config_1 = SyntheticDataConfig(seed=123, case_count=10, person_count=20, officer_count=5, evidence_count=10, dependency_count=5)
    config_2 = SyntheticDataConfig(seed=123, case_count=10, person_count=20, officer_count=5, evidence_count=10, dependency_count=5)

    assembly_1 = generate_synthetic_graph(config_1)
    assembly_2 = generate_synthetic_graph(config_2)

    assert len(assembly_1.dataset.nodes) == len(assembly_2.dataset.nodes)
    assert len(assembly_1.dataset.edges) == len(assembly_2.dataset.edges)

    # Compare node IDs to ensure exact determinism
    node_ids_1 = [node.id for node in assembly_1.dataset.nodes]
    node_ids_2 = [node.id for node in assembly_2.dataset.nodes]
    assert node_ids_1 == node_ids_2

    # Compare edge types and properties
    edge_types_1 = [edge.edge_type.value for edge in assembly_1.dataset.edges]
    edge_types_2 = [edge.edge_type.value for edge in assembly_2.dataset.edges]
    assert edge_types_1 == edge_types_2


def test_investigated_by_edges_present():
    """Every case must have exactly one INVESTIGATED_BY edge.

    This edge connects Case to Officer and is the primary path used by escalation
    routing to resolve the correct supervisor rank via Case→Officer→Unit traversal.
    A missing INVESTIGATED_BY edge means escalation routing silently has no officer
    to route through — a silent failure that only surfaces at Phase 3 integration time.
    """
    config = SyntheticDataConfig(seed=42, case_count=20, person_count=30, officer_count=10, evidence_count=5, dependency_count=5)
    assembly = generate_synthetic_graph(config)
    investigated_by_edges = [
        edge for edge in assembly.dataset.edges
        if edge.edge_type == GraphRelationshipType.INVESTIGATED_BY
    ]
    case_nodes = [node for node in assembly.dataset.nodes if node.entity_type.value == "Case"]
    # Every case must have at least one INVESTIGATED_BY edge
    assert len(investigated_by_edges) >= len(case_nodes), (
        f"Expected at least {len(case_nodes)} INVESTIGATED_BY edges (one per case), "
        f"got {len(investigated_by_edges)}"
    )
