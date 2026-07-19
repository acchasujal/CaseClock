"""tests/test_phase4_services.py

Phase 4/5/6 acceptance tests: service layer contracts.

Covers:
  - CaseService list_worklist, get_case_detail, update_dependency, list_escalations
  - CaseService audit events are emitted with actor_id
  - CopilotService prohibited inference refusal
  - CopilotService unsupported intent refusal
  - CopilotService case_status intent path
  - _is_prohibited check covers all prohibited terms
  - CopilotIntent enum covers expected intents
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.case_service import CaseService
from backend.app.services.copilot_service import (
    CopilotIntent,
    CopilotService,
    _is_prohibited,
)
from shared.contracts.api import CopilotQueryRequest, DependencyStatus, UserRole


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_repo() -> InMemoryBackendRepository:
    ref = datetime(2026, 7, 18, tzinfo=timezone.utc)
    return InMemoryBackendRepository(reference_time=ref)


def _principal(role: UserRole = UserRole.IO) -> Principal:
    return Principal(user_id=f"user-{role.value}", email=f"{role.value}@test.com", role=role)


class _FakeAuditRepo:
    def __init__(self):
        self.audit_events: list[dict] = []


def _audit_service(repo=None) -> AuditService:
    return AuditService(repo or _FakeAuditRepo())


# ── CaseService tests ──────────────────────────────────────────────────────────

class TestCaseService:
    def test_list_worklist_returns_cases(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        result = service.list_worklist(_principal(UserRole.SP))
        assert len(result) > 0
        assert result[0].fir_number

    def test_list_worklist_emits_audit_event(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        service.list_worklist(_principal(), request_id="req-1")
        # InMemoryBackendRepository also writes an audit event in list_worklist.
        # Filter for the service-emitted one by actor_id.
        events = [e for e in repo.audit_events if e["event_type"] == "worklist_viewed" and e.get("actor_id") == "user-IO"]
        assert len(events) >= 1
        assert events[0]["request_id"] == "req-1"

    def test_get_case_detail_returns_detail(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        worklist = service.list_worklist(_principal(UserRole.SP))
        case_id = worklist[0].id
        detail = service.get_case_detail(case_id, _principal())
        assert detail is not None
        assert detail.id == case_id
        assert isinstance(detail.clocks, list)

    def test_get_case_detail_returns_none_for_missing(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        result = service.get_case_detail("does-not-exist", _principal())
        assert result is None

    def test_get_case_detail_emits_audit_event(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        worklist = service.list_worklist(_principal(UserRole.SP))
        case_id = worklist[0].id
        service.get_case_detail(case_id, _principal(UserRole.SHO), request_id="req-2")
        # InMemoryBackendRepository also writes a case_viewed event; filter for ours.
        events = [
            e for e in repo.audit_events
            if e["event_type"] == "case_viewed" and e.get("actor_id") == "user-SHO"
        ]
        assert len(events) >= 1
        assert events[0]["case_id"] == case_id

    def test_update_dependency_returns_updated_response(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        # Find a case with a dependency
        for case_id in repo.case_ids:
            deps = repo.case_to_dependencies.get(case_id, [])
            if deps:
                dep_id = deps[0]
                result = service.update_dependency(dep_id, DependencyStatus.RESOLVED, _principal())
                assert result is not None
                assert result.status == DependencyStatus.RESOLVED
                return
        pytest.skip("No dependency in synthetic data")

    def test_update_dependency_returns_none_for_missing(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        result = service.update_dependency("no-dep", DependencyStatus.RESOLVED, _principal())
        assert result is None

    def test_list_escalations_returns_list(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        escalations = service.list_escalations(_principal(UserRole.SHO))
        assert isinstance(escalations, list)

    def test_get_case_network_returns_flow_shape(self):
        repo = _make_repo()
        service = CaseService(repo, _audit_service(repo))
        worklist = service.list_worklist(_principal(UserRole.SP))
        case_id = worklist[0].id
        network = service.get_case_network(case_id, _principal())
        assert network is not None
        assert "nodes" in network
        assert "edges" in network


# ── CopilotService tests ────────────────────────────────────────────────────────

class TestCopilotService:
    def _service(self, repo=None) -> CopilotService:
        r = repo or _make_repo()
        return CopilotService(r, _audit_service(r))

    def _request(self, query: str, case_id: str | None = None) -> CopilotQueryRequest:
        return CopilotQueryRequest(query=query, case_id=case_id, user_role=UserRole.IO)

    def test_refuses_guilty_inference(self):
        svc = self._service()
        response = svc.handle_query(self._request("is the accused guilty?"), _principal())
        assert response.refused
        assert "guilt" in (response.refusal_reason or "").lower()

    def test_refuses_culpable_term(self):
        svc = self._service()
        response = svc.handle_query(self._request("was he culpable?"), _principal())
        assert response.refused

    def test_refuses_reoffend_term(self):
        svc = self._service()
        response = svc.handle_query(self._request("will the accused reoffend?"), _principal())
        assert response.refused

    def test_refuses_predict_term(self):
        svc = self._service()
        response = svc.handle_query(self._request("predict next crime"), _principal())
        assert response.refused

    def test_case_id_scoped_query_returns_answer(self):
        repo = _make_repo()
        svc = self._service(repo)
        case_id = repo.case_ids[0]
        response = svc.handle_query(self._request("what is the status?", case_id=case_id), _principal())
        # May be refused only for prohibited terms; with a valid case_id it should answer
        assert not response.refused

    def test_refused_query_emits_copilot_refused_audit(self):
        repo = _make_repo()
        svc = self._service(repo)
        svc.handle_query(self._request("is the accused guilty?"), _principal(), request_id="req-x")
        events = [e for e in repo.audit_events if e["event_type"] == "copilot_refused"]
        assert events

    def test_unsupported_intent_returns_refusal(self):
        repo = _make_repo()
        svc = self._service(repo)
        # A query that doesn't match any case/clock/dependency/graph keyword
        response = svc.handle_query(self._request("translate this document to Kannada"), _principal())
        assert response.refused


# ── _is_prohibited tests ─────────────────────────────────────────────────────

class TestIsProhibited:
    def test_guilty_is_prohibited(self):
        assert _is_prohibited("is the accused guilty?")

    def test_culpable_is_prohibited(self):
        assert _is_prohibited("was she culpable?")

    def test_reoffend_is_prohibited(self):
        assert _is_prohibited("will they reoffend?")

    def test_predict_is_prohibited(self):
        assert _is_prohibited("predict future crimes")

    def test_case_status_is_allowed(self):
        assert not _is_prohibited("what is the clock status for this case?")

    def test_dependency_query_is_allowed(self):
        assert not _is_prohibited("what dependencies are pending?")

    def test_case_insensitive(self):
        assert _is_prohibited("Is He GUILTY?")


# ── CopilotIntent enum tests ────────────────────────────────────────────────────

class TestCopilotIntentEnum:
    def test_all_expected_intents_defined(self):
        expected = {"retrieve_cases", "aggregate", "graph_query", "case_status", "unsupported_request"}
        defined = {intent.value for intent in CopilotIntent}
        assert expected <= defined
