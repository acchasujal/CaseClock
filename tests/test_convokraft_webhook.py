from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app


def _client(settings: Settings | None = None) -> TestClient:
    return TestClient(create_app(InMemoryBackendRepository(), settings=settings or Settings(ENVIRONMENT="development")))


def _payload(action: str, role: str = "IO") -> dict:
    return {"todo": "execute", "bot": "voiceassistant", "action": action, "environment": "development", "params": {}, "userInput": "", "user": {"id": "demo-user"}, "clientData": {"role": role}}


def test_case_status_summary_uses_repository_worklist() -> None:
    client = _client()
    expected = client.get("/worklist?role=IO").json()
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "execution"
    assert body["data"]["active_case_count"] == len(expected)
    assert body["data"]["active_case_count"] > 0


def test_role_context_changes_worklist_scope() -> None:
    client = _client()
    sho_count = len(client.get("/worklist?role=SHO").json())
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary", "SHO"))

    assert response.status_code == 200
    assert response.json()["data"]["active_case_count"] == sho_count


def test_urgent_and_deadline_actions_use_clock_state() -> None:
    client = _client()
    urgent = client.post("/api/integrations/convokraft/action", json=_payload("urgent_cases")).json()
    deadlines = client.post("/api/integrations/convokraft/action", json=_payload("deadline_summary")).json()

    assert urgent["status"] == "execution"
    assert urgent["data"]["count"] == len(urgent["data"]["cases"])
    assert deadlines["data"]["overdue"] >= 0
    assert deadlines["data"]["red"] >= 0


def test_unsupported_and_malformed_payloads_are_controlled() -> None:
    client = _client()
    unsupported = client.post("/api/integrations/convokraft/action", json=_payload("unknown_action"))
    malformed = client.post("/api/integrations/convokraft/action", content=b"not-json", headers={"content-type": "application/json"})

    assert unsupported.status_code == 200
    assert "do not support" in unsupported.json()["message"]
    assert malformed.status_code == 400


def test_production_webhook_fails_closed_without_signature_configuration() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY=""))
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary"))
    assert response.status_code == 401
