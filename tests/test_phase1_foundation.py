"""tests/test_phase1_foundation.py

Phase 1 acceptance tests: production foundation and contract hardening.

Covers:
  - Settings load and CORS origin parsing
  - UTC clock abstraction (FrozenClock, SystemClock)
  - Request-ID correlation (middleware echo)
  - Error envelope structure for invalid inputs
  - Clock status threshold boundaries (exact -1/0/6/7/14/15 per plan §7)
  - Health endpoint returns version from settings
  - Worklist with invalid role returns 422 (Pydantic validation)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.core.clock.engine import ClockEngine, clock_status
from backend.app.core.time import FrozenClock, SystemClock, ensure_utc, utc_now
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from shared.contracts.api import ClockStatus


# ── Helpers ────────────────────────────────────────────────────────────────────

def _client(state_path=None) -> TestClient:
    repo = InMemoryBackendRepository(state_path=state_path)
    return TestClient(create_app(repo))


# ── Settings tests ─────────────────────────────────────────────────────────────

class TestSettings:
    def test_default_cors_origins_are_localhost(self):
        settings = Settings()
        assert "http://localhost:5173" in settings.cors_origins_list
        assert "http://127.0.0.1:5173" in settings.cors_origins_list

    def test_cors_origins_from_env(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://prod.example.com,https://api.example.com")
        settings = Settings()
        assert settings.cors_origins_list == [
            "https://prod.example.com",
            "https://api.example.com",
        ]

    def test_is_development_by_default(self):
        settings = Settings()
        assert settings.is_development

    def test_is_production_flag(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.is_production

    def test_effective_state_path_is_none_when_empty(self):
        settings = Settings()
        # Default STATE_PATH is empty string → None (disables persistence)
        assert settings.effective_state_path is None

    def test_effective_state_path_when_set(self, monkeypatch, tmp_path):
        monkeypatch.setenv("STATE_PATH", str(tmp_path / "state.json"))
        settings = Settings()
        assert settings.effective_state_path == tmp_path / "state.json"


# ── Clock abstraction tests ─────────────────────────────────────────────────────

class TestFrozenClock:
    def test_frozen_clock_always_returns_same_time(self):
        frozen = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
        clock = FrozenClock(frozen)
        assert clock.now() == frozen
        assert clock.now() == frozen  # idempotent

    def test_frozen_clock_rejects_naive_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            FrozenClock(datetime(2026, 7, 18, 12, 0, 0))  # naive

    def test_system_clock_returns_utc_aware(self):
        clock = SystemClock()
        now = clock.now()
        assert now.tzinfo is not None
        assert now.tzinfo.utcoffset(now).total_seconds() == 0.0

    def test_utc_now_is_aware(self):
        now = utc_now()
        assert now.tzinfo is not None

    def test_ensure_utc_on_naive_attaches_utc(self):
        naive = datetime(2026, 7, 18, 10, 0, 0)
        result = ensure_utc(naive)
        assert result.tzinfo is not None
        assert result == datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)

    def test_ensure_utc_on_aware_is_noop(self):
        aware = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(aware)
        assert result == aware


# ── Clock status boundary tests ────────────────────────────────────────────────
# Plan §7 specifies exact thresholds: <0 overdue, 0–6 red, 7–14 amber, >14 green

class TestClockStatusBoundaries:
    def test_negative_one_is_overdue(self):
        assert clock_status(-1) == ClockStatus.OVERDUE

    def test_zero_is_red(self):
        assert clock_status(0) == ClockStatus.RED

    def test_six_is_red(self):
        assert clock_status(6) == ClockStatus.RED

    def test_seven_is_amber(self):
        assert clock_status(7) == ClockStatus.AMBER

    def test_fourteen_is_amber(self):
        assert clock_status(14) == ClockStatus.AMBER

    def test_fifteen_is_green(self):
        assert clock_status(15) == ClockStatus.GREEN


# ── Request ID middleware tests ────────────────────────────────────────────────

class TestRequestIDMiddleware:
    def test_health_response_includes_request_id_header(self):
        client = _client()
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_supplied_request_id_is_echoed(self):
        client = _client()
        response = client.get("/health", headers={"X-Request-ID": "test-id-123"})
        assert response.headers["X-Request-ID"] == "test-id-123"

    def test_generated_request_id_is_a_uuid(self):
        import uuid
        client = _client()
        response = client.get("/health")
        request_id = response.headers["X-Request-ID"]
        # Should not raise ValueError
        uuid.UUID(request_id)


# ── Health endpoint ────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        client = _client()
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "caseclock-backend"

    def test_health_returns_version(self):
        client = _client()
        response = client.get("/health")
        body = response.json()
        assert "version" in body
        assert body["version"]  # not empty


# ── Error envelope tests ───────────────────────────────────────────────────────

class TestErrorEnvelope:
    def test_invalid_role_returns_422_not_500(self):
        """Invalid query param must yield 422 (Pydantic validation), not 500."""
        client = _client()
        response = client.get("/worklist?role=INVALID")
        assert response.status_code == 422

    def test_unknown_case_id_returns_404(self):
        client = _client()
        response = client.get("/cases/does-not-exist-id")
        assert response.status_code == 404

    def test_unknown_dependency_id_returns_404(self):
        client = _client()
        response = client.patch(
            "/deps/does-not-exist-dep",
            json={"status": "resolved"},
        )
        assert response.status_code == 404

    def test_copilot_missing_user_role_returns_422(self):
        """CopilotQueryRequest.user_role is required by the shared contract."""
        client = _client()
        response = client.post(
            "/copilot/query",
            json={"query": "any query"},  # missing user_role
        )
        assert response.status_code == 422


# ── ClockEngine with FrozenClock integration ───────────────────────────────────

class TestClockEngineWithFrozenTime:
    def test_frozen_time_produces_deterministic_days_remaining(self):
        frozen = datetime(2026, 7, 18, tzinfo=timezone.utc)
        engine = ClockEngine(reference_time=frozen)
        clock = engine.from_case(
            "case-x",
            {
                "offence_category": "theft",
                "reported_at": "2026-07-01T00:00:00+00:00",
            },
        )
        # 2026-07-01 + 60 days = 2026-08-30; 2026-08-30 - 2026-07-18 = 43 days
        assert clock.days_remaining == 43
        assert clock.status == ClockStatus.GREEN

    def test_clock_engine_uses_deadline_from_node(self):
        frozen = datetime(2026, 7, 18, tzinfo=timezone.utc)
        engine = ClockEngine(reference_time=frozen)
        clock = engine.from_clock_node(
            "clock-1",
            {
                "start_date": "2026-07-01T00:00:00+00:00",
                "deadline_date": "2026-07-20T00:00:00+00:00",
                "clock_type": "investigation_60_day",
            },
        )
        # 2026-07-20 - 2026-07-18 = 2 days
        assert clock.days_remaining == 2
        assert clock.status == ClockStatus.RED

    def test_clock_engine_overdue_when_deadline_passed(self):
        frozen = datetime(2026, 8, 1, tzinfo=timezone.utc)
        engine = ClockEngine(reference_time=frozen)
        clock = engine.from_clock_node(
            "clock-2",
            {
                "start_date": "2026-06-01T00:00:00+00:00",
                "deadline_date": "2026-07-20T00:00:00+00:00",
                "clock_type": "investigation_60_day",
            },
        )
        assert clock.days_remaining < 0
        assert clock.status == ClockStatus.OVERDUE
