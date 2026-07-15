"""
graph/repositories/graph_repository.py

Bridge between persistent database and in-memory GraphStore.
Currently stubs the DB layer — Dev 1 will wire real models.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge


class GraphRepository:
    """
    Loads and persists graph data from/to the database.
    
    For now, operates on an injected GraphStore (in-memory).
    When Dev 1 provides DB models, replace the load methods
    with SQL queries that build NodeRecord/AdjEdge objects.
    """

    def __init__(self, store: GraphStore | None = None) -> None:
        self._store = store or GraphStore()
        self._db_session: Any = None  # Dev 1 will inject this

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def store(self) -> GraphStore:
        """Return the current in-memory graph."""
        return self._store

    def load_from_db(self, session: Any) -> GraphStore:
        """
        Load entire graph from database into memory.
        
        TODO: Dev 1 — replace with real SQLAlchemy/Catalyst queries:
        
        cases = session.query(Case).all()
        for case in cases:
            self._add_node(case.id, "Case", { ...case fields... })
            for accused in case.accused:
                self._add_node(accused.person_id, "Person", { ... })
                self._add_edge(accused.person_id, case.id, "ACCUSED_IN")
        """
        self._db_session = session
        # For now, return whatever store was injected
        return self._store

    def refresh(self) -> GraphStore:
        """Reload graph from database (call after mutations)."""
        self._store = GraphStore()
        if self._db_session:
            self.load_from_db(self._db_session)
        return self._store

    def get_case(self, case_id: str) -> NodeRecord | None:
        """Fetch a single case node by ID."""
        return self._store.nodes.get(case_id)

    def get_person(self, person_id: str) -> NodeRecord | None:
        """Fetch a single person node by ID."""
        return self._store.nodes.get(person_id)

    def get_cases_for_person(self, person_id: str, role: str | None = None) -> list[NodeRecord]:
        """
        Return all cases a person is involved in.
        Optional role filter: "ACCUSED_IN", "VICTIM_IN", etc.
        """
        results: list[NodeRecord] = []
        for edge in self._store.adj.get(person_id, []):
            if role and edge.edge_type != role:
                continue
            case_node = self._store.nodes.get(edge.target_id)
            if case_node and case_node.entity_type == "Case":
                results.append(case_node)
        return results

    def get_persons_for_case(self, case_id: str, role: str | None = None) -> list[NodeRecord]:
        """
        Return all persons linked to a case.
        Optional role filter: "ACCUSED_IN", "VICTIM_IN", etc.
        """
        results: list[NodeRecord] = []
        # Check reverse adjacency (person -> case edges)
        for person_id, edges in self._store.adj.items():
            for edge in edges:
                if edge.target_id == case_id:
                    if role and edge.edge_type != role:
                        continue
                    person_node = self._store.nodes.get(person_id)
                    if person_node and person_node.entity_type == "Person":
                        results.append(person_node)
        return results

    # ── Internal helpers (for Dev 1 to extend) ─────────────────────────────

    def _add_node(self, node_id: str, entity_type: str, properties: dict) -> None:
        """Add or update a node in the store."""
        self._store.nodes[node_id] = NodeRecord(
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
        )

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, properties: dict | None = None) -> None:
        """Add an edge to the store and update adjacency index."""
        edge = AdjEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
        )
        self._store.edge_index.setdefault(edge_type, []).append(edge)
        self._store.adj.setdefault(source_id, []).append(edge)