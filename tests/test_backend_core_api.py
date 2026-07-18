from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.db.in_memory import InMemoryBackendRepository


def test_worklist_and_case_detail_contracts():
    client = _client()

    response = client.get("/worklist?role=IO")

    assert response.status_code == 200
    worklist = response.json()
    assert worklist
    first_case = worklist[0]
    assert first_case["fir_number"]
    assert first_case["clock"]["status"] in {"green", "amber", "red", "overdue"}

    detail_response = client.get(f"/cases/{first_case['id']}")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == first_case["id"]
    assert isinstance(detail["clocks"], list)
    assert isinstance(detail["dependencies"], list)


def test_dependency_update_refreshes_case_state():
    client = _client()
    case_id = _case_with_dependency(client)
    detail = client.get(f"/cases/{case_id}").json()
    dependency_id = detail["dependencies"][0]["id"]

    response = client.patch(f"/deps/{dependency_id}", json={"status": "resolved"})

    assert response.status_code == 200
    dependency = response.json()
    assert dependency["status"] == "resolved"
    assert dependency["days_stale"] == 0


def test_escalations_are_available_and_templated():
    client = _client()

    response = client.get("/escalations")

    assert response.status_code == 200
    escalations = response.json()
    assert escalations
    assert "pending" in escalations[0]["reason"] or "remaining" in escalations[0]["reason"]


def test_copilot_refuses_guilt_inference():
    client = _client()

    response = client.post(
        "/copilot/query",
        json={"query": "is the accused guilty?", "user_role": "IO"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert "guilt" in body["refusal_reason"]


def test_case_network_uses_frontend_shape():
    client = _client()
    case_id = client.get("/worklist?role=IO").json()[0]["id"]

    response = client.get(f"/cases/{case_id}/network")

    assert response.status_code == 200
    body = response.json()
    assert body["nodes"]
    assert body["edges"]
    assert {"id", "type", "data", "position"} <= set(body["nodes"][0])
    assert {"id", "source", "target", "label"} <= set(body["edges"][0])


def test_audit_endpoint_records_core_events():
    client = _client()
    case_id = client.get("/worklist?role=IO").json()[0]["id"]

    client.get(f"/cases/{case_id}")
    client.post(
        "/copilot/query",
        json={"query": "is the accused guilty?", "case_id": case_id, "user_role": "IO"},
    )
    response = client.get("/audit?limit=10")

    assert response.status_code == 200
    event_types = {event["event_type"] for event in response.json()}
    assert "worklist_viewed" in event_types
    assert "case_viewed" in event_types
    assert "copilot_refused" in event_types


def test_dependency_state_can_persist_to_file(tmp_path):
    state_path = tmp_path / "backend_state.json"
    repo = InMemoryBackendRepository(state_path=state_path)
    client = TestClient(create_app(repo))
    case_id = _case_with_dependency(client)
    dependency_id = client.get(f"/cases/{case_id}").json()["dependencies"][0]["id"]

    client.patch(f"/deps/{dependency_id}", json={"status": "resolved"})

    reloaded = InMemoryBackendRepository(state_path=state_path)
    dependency_node = reloaded.nodes[dependency_id]
    assert dependency_node["status"] == "resolved"
    assert state_path.exists()


def _case_with_dependency(client: TestClient) -> str:
    for summary in client.get("/worklist?role=SP").json():
        detail = client.get(f"/cases/{summary['id']}").json()
        if detail["dependencies"]:
            return summary["id"]
    raise AssertionError("Expected synthetic data to include at least one dependency")


def _client() -> TestClient:
    return TestClient(create_app(InMemoryBackendRepository()))
