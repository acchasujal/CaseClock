"""tests/test_system_status.py

Unit and integration tests for the autonomous deadline monitor status API.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.cron_service import CronService
from backend.app.db.in_memory import InMemoryBackendRepository


@pytest.fixture
def repo():
    return InMemoryBackendRepository()


@pytest.fixture
def app(repo):
    return create_app(repository=repo)


@pytest.fixture
def client(app):
    return TestClient(app)


def test_status_when_no_sweep_exists(client):
    """GET /api/v1/system/deadline-monitor/status returns unavailable status when no sweep has run."""
    response = client.get("/api/v1/system/deadline-monitor/status?role=IO")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "unavailable"
    assert data["schedule"]["type"] == "recursive"
    assert data["schedule"]["interval_minutes"] == 15
    assert data["last_run"] is None


def test_status_when_recent_sweep_exists(repo, client):
    """GET /api/v1/system/deadline-monitor/status returns active status for recent sweep."""
    audit_svc = AuditService(repository=repo)
    cron_svc = CronService(repository=repo, audit_service=audit_svc)

    # Run sweep
    sweep_res = cron_svc.run_deadline_sweep()
    assert sweep_res["status"] == "ok"

    response = client.get("/api/v1/system/deadline-monitor/status?role=SHO")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "active"
    assert data["last_run"] is not None
    assert data["last_run"]["run_id"] == sweep_res["run_id"]
    assert data["last_run"]["cases_scanned"] == sweep_res["cases_scanned"]
    assert data["last_run"]["clocks_evaluated"] == sweep_res["clocks_evaluated"]
    assert data["last_run"]["state_transitions"] == sweep_res["state_transitions"]
    assert data["last_run"]["escalations_created"] == sweep_res["escalations_created"]
    assert "CRON_SECRET" not in str(data)


def test_status_when_stale_sweep_exists(repo, client):
    """GET /api/v1/system/deadline-monitor/status returns delayed status for old sweep."""
    audit_svc = AuditService(repository=repo)

    # Simulate an audit event completed 45 minutes ago
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    audit_svc.record(
        AuditEventType.DEADLINE_SWEEP_COMPLETED,
        actor_id="system-cron",
        run_id="cron-run-stale-123",
        completed_at=old_time,
        status="ok",
        cases_scanned=300,
        clocks_evaluated=400,
        state_transitions=5,
        escalations_created=5,
        errors=0,
        duration_ms=12.5,
    )

    response = client.get("/api/v1/system/deadline-monitor/status?role=SP")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "delayed"
    assert data["last_run"]["run_id"] == "cron-run-stale-123"
    assert data["last_run"]["cases_scanned"] == 300


def test_role_authorization_and_no_secret_leak(client):
    """All valid roles can access status and cron secret is never exposed."""
    for role in ["IO", "SHO", "SP"]:
        res = client.get(f"/api/v1/system/deadline-monitor/status?role={role}")
        assert res.status_code == 200
        body_text = res.text
        assert "CRON_SECRET" not in body_text
        assert "cc_cron_sec" not in body_text
