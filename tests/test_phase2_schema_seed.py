"""tests/test_phase2_schema_seed.py

Phase 2 acceptance tests: schema definitions and seed tooling.

Covers:
  - Schema DDL completeness (all expected tables defined)
  - TABLE_CREATION_ORDER consistency
  - Seed dry-run completes with GraphLoader validation
  - Repository interfaces are properly defined ABCs
  - Entity type to table mapping covers all graph entity types
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.db.migrations.schema import (
    SCHEMA_DDL,
    TABLE_CREATION_ORDER,
    SCHEMA_VERSION,
)
from backend.app.db.seed.import_synthetic import (
    ENTITY_TYPE_TO_TABLE,
    DEFAULT_ARTIFACT,
    run_seed,
)


class TestSchemaDefinitions:
    def test_schema_version_is_set(self):
        assert SCHEMA_VERSION  # not empty

    def test_schema_ddl_defines_expected_tables(self):
        table_names = {name for name, _ in SCHEMA_DDL}
        required = {
            "schema_migration", "seed_run",
            "case", "person", "officer", "unit",
            "court", "location", "act", "section",
            "crime_head", "crime_sub_head", "evidence",
            "dependency", "clock_instance",
            "escalation_event", "conversation_log",
            "audit_event", "graph_edge",
        }
        assert required <= table_names, f"Missing tables: {required - table_names}"

    def test_creation_order_contains_all_ddl_tables(self):
        ddl_tables = {name for name, _ in SCHEMA_DDL}
        order_tables = set(TABLE_CREATION_ORDER)
        assert ddl_tables == order_tables, (
            f"DDL vs order mismatch — extra in DDL: {ddl_tables - order_tables}; "
            f"extra in order: {order_tables - ddl_tables}"
        )

    def test_creation_order_has_no_duplicates(self):
        assert len(TABLE_CREATION_ORDER) == len(set(TABLE_CREATION_ORDER))

    def test_each_ddl_entry_has_create_table(self):
        for name, ddl in SCHEMA_DDL:
            assert "CREATE TABLE" in ddl.upper(), f"Table {name} DDL missing CREATE TABLE"


class TestSeedImporter:
    def test_entity_type_to_table_covers_all_graph_entity_types(self):
        """All entity types in the synthetic artifact should have table mappings."""
        expected_types = {
            "Case", "Person", "Officer", "Unit", "Court", "Location",
            "Act", "Section", "CrimeHead", "CrimeSubHead", "Evidence",
            "Dependency", "ClockInstance",
        }
        assert expected_types <= set(ENTITY_TYPE_TO_TABLE.keys()), (
            f"Missing entity types: {expected_types - set(ENTITY_TYPE_TO_TABLE.keys())}"
        )

    def test_default_artifact_exists(self):
        """The synthetic artifact used as seed source must exist."""
        assert DEFAULT_ARTIFACT.exists(), (
            f"Synthetic artifact not found: {DEFAULT_ARTIFACT}\n"
            "Run: python artifacts/synthetic_graph/generate.py"
        )

    def test_seed_dry_run_passes_validation(self):
        """Full dry-run must succeed: GraphLoader validates all nodes and edges."""
        result = run_seed(artifact_path=DEFAULT_ARTIFACT, dry_run=True)
        assert result["status"] == "dry_run_ok"
        assert result["checksum"]
        assert result.get("Case", 0) > 0, "Expected at least one Case node"
        assert result.get("Officer", 0) > 0, "Expected at least one Officer node"
        assert result.get("Dependency", 0) > 0, "Expected at least one Dependency node"
        assert result.get("ClockInstance", 0) > 0, "Expected at least one ClockInstance node"

    def test_seed_dry_run_with_missing_artifact_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            run_seed(artifact_path=missing, dry_run=True)


class TestRepositoryInterfaces:
    """Verify repository ABCs cannot be instantiated without implementing all methods."""

    def test_case_repository_is_abstract(self):
        from backend.app.db.repositories.interfaces import CaseRepository
        with pytest.raises(TypeError):
            CaseRepository()  # type: ignore[abstract]

    def test_dependency_repository_is_abstract(self):
        from backend.app.db.repositories.interfaces import DependencyRepository
        with pytest.raises(TypeError):
            DependencyRepository()  # type: ignore[abstract]

    def test_escalation_repository_is_abstract(self):
        from backend.app.db.repositories.interfaces import EscalationRepository
        with pytest.raises(TypeError):
            EscalationRepository()  # type: ignore[abstract]

    def test_audit_repository_is_abstract(self):
        from backend.app.db.repositories.interfaces import AuditRepository
        with pytest.raises(TypeError):
            AuditRepository()  # type: ignore[abstract]
