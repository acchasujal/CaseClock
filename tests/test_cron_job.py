"""tests/test_cron_job.py

Comprehensive tests for the scheduled deadline sweep job endpoint (/internal/jobs/deadline-sweep).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.db.in_memory import InMemoryBackendRepository


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-key-12345")
    from backend.app.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo, settings=settings)
    yield TestClient(app), repo
    get_settings.cache_clear()


def test_cron_missing_auth_header_rejected(app_client):
    client, repo = app_client
    response = client.post("/internal/jobs/deadline-sweep")
    assert response.status_code == 401
    assert "Cron authentication failed" in response.json()["detail"]


def test_cron_wrong_auth_secret_rejected(app_client):
    client, repo = app_client
    headers = {"X-CaseClock-Cron-Secret": "wrong-secret"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 401
    assert "Invalid or missing cron secret" in response.json()["detail"]


def test_cron_unset_server_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    from backend.app.config import get_settings
    get_settings.cache_clear()
    empty_settings = get_settings()
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo, settings=empty_settings)
    client = TestClient(app)

    headers = {"X-CaseClock-Cron-Secret": "test-secret-key-12345"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 401
    assert "CRON_SECRET is not configured on the server" in response.json()["detail"]
    get_settings.cache_clear()


def test_cron_demo_auth_header_does_not_bypass_cron_auth(app_client):
    client, repo = app_client
    # User passes X-Dev-Role or demo auth headers but NO valid cron secret
    headers = {"X-Dev-Role": "SP"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 401


def test_cron_valid_secret_header_executes_sweep(app_client):
    client, repo = app_client
    headers = {"X-CaseClock-Cron-Secret": "test-secret-key-12345"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["run_id"].startswith("cron-run-")
    assert data["cases_scanned"] > 0
    assert data["clocks_evaluated"] > 0
    assert "state_transitions" in data
    assert "escalations_created" in data
    assert data["errors"] == 0
    assert data["duration_ms"] >= 0


def test_cron_valid_bearer_token_auth_executes_sweep(app_client):
    client, repo = app_client
    headers = {"Authorization": "Bearer test-secret-key-12345"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cron_idempotency_second_run_no_duplicate_domain_transitions(app_client):
    client, repo = app_client
    headers = {"X-CaseClock-Cron-Secret": "test-secret-key-12345"}

    # First sweep
    r1 = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert r1.status_code == 200
    d1 = r1.json()

    # Second sweep with unchanged data
    r2 = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()

    # Second run should report zero new state transitions and zero new escalations
    assert d2["state_transitions"] == 0
    assert d2["escalations_created"] == 0
    # Each run still receives its own unique operational run_id
    assert d1["run_id"] != d2["run_id"]


def test_cron_inactive_case_filtering(app_client):
    client, repo = app_client
    # Add a closed case node to repository
    closed_case_id = "test-closed-case-999"
    repo.nodes[closed_case_id] = {
        "id": closed_case_id,
        "entity_type": "Case",
        "case_stage": "closed",
        "fir_number": "FIR/TEST/CLOSED",
        "police_station": "Ashok Nagar",
        "offence_category": "theft",
    }
    repo.case_ids.append(closed_case_id)

    headers = {"X-CaseClock-Cron-Secret": "test-secret-key-12345"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 200
    # Sweep completes cleanly without throwing errors on closed cases
    assert response.json()["errors"] == 0


def test_cron_error_isolation_on_malformed_case(app_client):
    client, repo = app_client
    # Corrupt one case's clocks method to raise an unexpected exception
    corrupt_case_id = repo.case_ids[0]

    original_case_clocks = repo._case_clocks

    def flaky_case_clocks(case_id, case_node):
        if case_id == corrupt_case_id:
            raise RuntimeError("Simulated database read failure for test")
        return original_case_clocks(case_id, case_node)

    repo._case_clocks = flaky_case_clocks

    headers = {"X-CaseClock-Cron-Secret": "test-secret-key-12345"}
    response = client.post("/internal/jobs/deadline-sweep", headers=headers)
    assert response.status_code == 200

    data = response.json()
    # Malformed case recorded in errors count without halting remaining cases
    assert data["errors"] >= 1
    assert data["cases_scanned"] > 0


def test_existing_core_routes_unaffected(app_client):
    client, repo = app_client
    # Verify existing /health and worklist endpoints still function as expected
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    worklist_resp = client.get("/worklist", headers={"X-Dev-Role": "IO"})
    assert worklist_resp.status_code == 200
    assert isinstance(worklist_resp.json(), list)
