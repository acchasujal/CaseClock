"""tests/test_phase3_auth_audit.py

Phase 3 acceptance tests: authentication, authorization, and durable audit.

Covers:
  - Principal model (roles, capability checks)
  - DevelopmentVerifier (X-Dev-Role header extraction)
  - DevelopmentVerifier refuses in production mode
  - make_verifier factory (dev vs production selection)
  - AuditService enum taxonomy completeness
  - AuditService best-effort write (no exceptions raised on write failure)
  - AuditService list_events filtering
  - CatalystAuthVerifier is a stub (raises ForbiddenError with clear message)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.principal import Principal
from backend.app.auth.verifier import (
    CatalystAuthVerifier,
    DevelopmentVerifier,
    make_verifier,
)
from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import UserRole


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_request(headers: dict | None = None):
    """Build a minimal mock request object."""
    request = MagicMock()
    request.headers = headers or {}
    request.app.state.settings = Settings()
    return request


# ── Principal tests ────────────────────────────────────────────────────────────

class TestPrincipal:
    def test_principal_is_frozen(self):
        p = Principal(user_id="1", email="a@b.com", role=UserRole.IO)
        with pytest.raises((AttributeError, TypeError)):
            p.role = UserRole.SP  # type: ignore[misc]

    def test_anonymous_principal_is_anonymous(self):
        p = Principal.anonymous()
        assert p.is_anonymous

    def test_anonymous_principal_has_io_role(self):
        p = Principal.anonymous()
        assert p.role == UserRole.IO

    def test_io_can_view_worklist(self):
        p = Principal(user_id="u1", email="a@b.com", role=UserRole.IO)
        assert p.can_view_worklist()

    def test_io_cannot_access_sho_features(self):
        p = Principal(user_id="u1", email="a@b.com", role=UserRole.IO)
        assert not p.can_access_sho_features()

    def test_sho_can_access_sho_features(self):
        p = Principal(user_id="u2", email="b@b.com", role=UserRole.SHO)
        assert p.can_access_sho_features()

    def test_sp_can_access_sp_features(self):
        p = Principal(user_id="u3", email="c@b.com", role=UserRole.SP)
        assert p.can_access_sp_features()

    def test_sho_cannot_access_sp_features(self):
        p = Principal(user_id="u2", email="b@b.com", role=UserRole.SHO)
        assert not p.can_access_sp_features()

    def test_io_cannot_view_audit_log(self):
        p = Principal(user_id="u1", email="a@b.com", role=UserRole.IO)
        assert not p.can_view_audit_log()

    def test_sho_can_view_audit_log(self):
        p = Principal(user_id="u2", email="b@b.com", role=UserRole.SHO)
        assert p.can_view_audit_log()


# ── DevelopmentVerifier tests ──────────────────────────────────────────────────

class TestDevelopmentVerifier:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_default_role_is_io_when_no_header(self):
        verifier = DevelopmentVerifier()
        request = _make_request({})
        principal = self._run(verifier.verify(request))
        assert principal.role == UserRole.IO

    def test_extracts_sho_role_from_header(self):
        verifier = DevelopmentVerifier()
        request = _make_request({"X-Dev-Role": "SHO"})
        principal = self._run(verifier.verify(request))
        assert principal.role == UserRole.SHO

    def test_extracts_sp_role_from_header(self):
        verifier = DevelopmentVerifier()
        request = _make_request({"X-Dev-Role": "SP"})
        principal = self._run(verifier.verify(request))
        assert principal.role == UserRole.SP

    def test_case_insensitive_role_header(self):
        verifier = DevelopmentVerifier()
        request = _make_request({"X-Dev-Role": "sho"})
        principal = self._run(verifier.verify(request))
        assert principal.role == UserRole.SHO

    def test_unknown_role_defaults_to_io(self):
        verifier = DevelopmentVerifier()
        request = _make_request({"X-Dev-Role": "COMMISSIONER"})
        principal = self._run(verifier.verify(request))
        assert principal.role == UserRole.IO

    def test_refuses_in_production_mode(self):
        from backend.app.api.errors import ForbiddenError
        verifier = DevelopmentVerifier(is_production=True)
        request = _make_request({"X-Dev-Role": "IO"})
        with pytest.raises(ForbiddenError):
            self._run(verifier.verify(request))

    def test_principal_is_anonymous_in_dev_mode(self):
        verifier = DevelopmentVerifier()
        request = _make_request({"X-Dev-Role": "SHO"})
        principal = self._run(verifier.verify(request))
        assert principal.is_anonymous


# ── CatalystAuthVerifier stub tests ────────────────────────────────────────────

class TestCatalystAuthVerifier:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_raises_on_empty_client_id(self):
        with pytest.raises(ValueError, match="client_id"):
            CatalystAuthVerifier(client_id="", project_id="proj-123")

    def test_raises_on_empty_project_id(self):
        with pytest.raises(ValueError, match="project_id"):
            CatalystAuthVerifier(client_id="client-123", project_id="")

    def test_verify_raises_forbidden_when_called(self):
        from backend.app.api.errors import ForbiddenError
        verifier = CatalystAuthVerifier(client_id="c", project_id="p")
        request = _make_request()
        with pytest.raises(ForbiddenError):
            self._run(verifier.verify(request))


# ── make_verifier factory tests ────────────────────────────────────────────────

class TestMakeVerifier:
    def test_returns_dev_verifier_without_catalyst_credentials(self):
        settings = Settings()  # no CATALYST_* env vars → empty strings
        verifier = make_verifier(settings)
        assert isinstance(verifier, DevelopmentVerifier)

    def test_returns_catalyst_verifier_with_credentials(self, monkeypatch):
        monkeypatch.setenv("CATALYST_CLIENT_ID", "client-123")
        monkeypatch.setenv("CATALYST_PROJECT_ID", "proj-456")
        settings = Settings()
        verifier = make_verifier(settings)
        assert isinstance(verifier, CatalystAuthVerifier)


# ── AuditService tests ─────────────────────────────────────────────────────────

class _FakeRepo:
    def __init__(self):
        self.audit_events: list[dict] = []


class TestAuditService:
    def test_record_appends_event_to_repo(self):
        repo = _FakeRepo()
        service = AuditService(repo)
        service.record(AuditEventType.CASE_VIEWED, case_id="case-1", request_id="req-1")
        assert len(repo.audit_events) == 1
        assert repo.audit_events[0]["event_type"] == "case_viewed"
        assert repo.audit_events[0]["case_id"] == "case-1"
        assert repo.audit_events[0]["request_id"] == "req-1"

    def test_record_never_raises(self):
        """AuditService must swallow exceptions — never propagate."""
        class BrokenRepo:
            @property
            def audit_events(self):
                raise RuntimeError("DB is down")
        service = AuditService(BrokenRepo())
        # Should not raise
        service.record(AuditEventType.WORKLIST_VIEWED)

    def test_list_events_filters_by_case_id(self):
        repo = _FakeRepo()
        service = AuditService(repo)
        service.record(AuditEventType.CASE_VIEWED, case_id="case-A")
        service.record(AuditEventType.CASE_VIEWED, case_id="case-B")
        events = service.list_events(case_id="case-A")
        assert len(events) == 1
        assert events[0]["case_id"] == "case-A"

    def test_list_events_filters_by_event_type(self):
        repo = _FakeRepo()
        service = AuditService(repo)
        service.record(AuditEventType.CASE_VIEWED, case_id="case-1")
        service.record(AuditEventType.COPILOT_REFUSED, case_id="case-1")
        events = service.list_events(event_type=AuditEventType.COPILOT_REFUSED)
        assert len(events) == 1
        assert events[0]["event_type"] == "copilot_refused"

    def test_list_events_respects_limit(self):
        repo = _FakeRepo()
        service = AuditService(repo)
        for i in range(10):
            service.record(AuditEventType.WORKLIST_VIEWED)
        events = service.list_events(limit=5)
        assert len(events) == 5

    def test_audit_event_type_enum_covers_required_events(self):
        """All events referenced in route handlers must exist in the enum."""
        required = {
            "worklist_viewed", "case_viewed", "case_network_viewed",
            "dependency_updated", "escalations_viewed", "manual_escalation_created",
            "copilot_answered", "copilot_refused",
            "access_denied", "token_invalid",
            "seed_started", "seed_completed", "seed_failed",
            "graph_query_executed",
        }
        defined = {event.value for event in AuditEventType}
        assert required <= defined, f"Missing from enum: {required - defined}"

    def test_event_has_uuid_id(self):
        import uuid
        repo = _FakeRepo()
        service = AuditService(repo)
        service.record(AuditEventType.CASE_VIEWED, case_id="case-1")
        event_id = repo.audit_events[0]["id"]
        uuid.UUID(event_id)  # must not raise

    def test_event_has_utc_occurred_at(self):
        repo = _FakeRepo()
        service = AuditService(repo)
        service.record(AuditEventType.CASE_VIEWED)
        occurred_at = repo.audit_events[0]["occurred_at"]
        # Must be parseable as ISO-8601
        dt = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None
