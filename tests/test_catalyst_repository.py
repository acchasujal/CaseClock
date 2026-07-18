from datetime import datetime, timezone

from backend.app.db.catalyst import CatalystBackendRepository
from shared.contracts.api import DependencyStatus


def test_catalyst_repository_reads_imported_table_shapes():
    repo = CatalystBackendRepository(
        catalyst_app=_FakeCatalystApp(),
        reference_time=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )

    worklist = repo.list_worklist("SP")
    detail = repo.get_case_detail("case-1")

    assert worklist[0].fir_number == "FIR/BEN/0001"
    assert detail is not None
    assert detail.clocks[0].clock_type == "investigation_60_day"
    assert detail.dependencies[0].name == "FSL report"


def test_catalyst_repository_updates_dependency_row():
    app = _FakeCatalystApp()
    repo = CatalystBackendRepository(
        catalyst_app=app,
        reference_time=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )

    dependency = repo.update_dependency("dep-1", DependencyStatus.RESOLVED)

    assert dependency is not None
    assert dependency.status == DependencyStatus.RESOLVED
    assert app.datastore().table("dependencies").updated_rows[0]["ROWID"] == "dep-row-1"
    assert app.datastore().table("dependencies").updated_rows[0]["status"] == "resolved"


class _FakeCatalystApp:
    def __init__(self) -> None:
        self._datastore = _FakeDatastore()

    def datastore(self):
        return self._datastore


class _FakeDatastore:
    def __init__(self) -> None:
        self.tables = {
            "cases": _FakeTable(
                [
                    {
                        "ROWID": "case-row-1",
                        "id": "case-1",
                        "fir_number": "FIR/BEN/0001",
                        "case_number": "CC-0001",
                        "district": "Bengaluru City",
                        "police_station": "Ashok Nagar",
                        "case_stage": "investigation",
                        "offence_category": "theft",
                        "reported_at": "2026-07-08 09:37:39",
                        "incident_at": "2026-07-08 00:37:39",
                        "risk_band": "amber",
                        "repeat_cluster_id": "",
                    }
                ]
            ),
            "clock_instances": _FakeTable(
                [
                    {
                        "ROWID": "clock-row-1",
                        "id": "clock-1",
                        "case_id": "case-1",
                        "clock_type": "investigation_60_day",
                        "start_date": "2026-07-08 09:37:39",
                        "deadline_date": "2026-07-28 09:37:39",
                        "days_remaining": 10,
                        "status": "amber",
                        "bnss_reference": "BNSS [UNVERIFIED]",
                        "stage": "investigation",
                    }
                ]
            ),
            "dependencies": _FakeTable(
                [
                    {
                        "ROWID": "dep-row-1",
                        "id": "dep-1",
                        "case_id": "case-1",
                        "dependency_type": "FSL report",
                        "status": "pending",
                        "requested_at": "2026-07-01 09:37:39",
                        "due_at": "2026-07-10 09:37:39",
                        "resolved_at": "",
                        "assigned_to_officer_id": "officer-1",
                        "days_stale": 17,
                        "notes": "Pending lab report.",
                    }
                ]
            ),
            "graph_nodes": _FakeTable([]),
            "graph_edges": _FakeTable([]),
            "audit_events": _FakeTable([]),
            "escalations": _FakeTable([]),
        }

    def table(self, table_name: str):
        return self.tables[table_name]


class _FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.inserted_rows: list[dict] = []
        self.updated_rows: list[dict] = []

    def get_iterable_rows(self):
        yield from self.rows

    def insert_row(self, row: dict):
        self.inserted_rows.append(row)
        return row

    def update_row(self, row: dict):
        self.updated_rows.append(row)
        return row
