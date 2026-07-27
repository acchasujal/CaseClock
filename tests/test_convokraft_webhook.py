from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app


def _client(settings: Settings | None = None) -> TestClient:
    return TestClient(create_app(InMemoryBackendRepository(), settings=settings or Settings(ENVIRONMENT="development")))


def _payload(action: str, role: str = "IO") -> dict:
    return {"todo": "execute", "bot": "voiceassistant", "action": action, "environment": "development", "params": {}, "userInput": "", "user": {"id": "demo-user"}, "clientData": {"role": role}}


def _realistic_payload(action: str, params: dict | None = None) -> dict:
    return {
        "todo": "execute",
        "bot": "voiceassistant",
        "action": action,
        "button_id": "",
        "environment": "development",
        "params": params or {},
        "userInput": "",
        "previousParam": "",
        "user": {"id": "demo-user"},
        "org": {},
        "broadcast": {},
        "cache": {},
        "sessionData": {},
        "clientData": {"role": "IO"},
    }


def _assert_execution_contract(response) -> None:
    assert response.status_code == 200
    assert set(response.json()) == {"status", "message", "card", "data", "broadcast", "trigger", "followup"}
    assert response.json()["status"] == "execution"


def test_case_status_summary_uses_repository_worklist() -> None:
    client = _client()
    expected = client.get("/worklist?role=IO").json()
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "execution"
    assert body["data"]["active_case_count"] == len(expected)
    assert body["data"]["active_case_count"] > 0


def test_realistic_case_status_summary_uses_catalyst_execution_contract() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=False))
    response = client.post("/api/integrations/convokraft/action", json=_realistic_payload("CaseStatusSummary"))

    _assert_execution_contract(response)
    assert response.json()["data"]["active_case_count"] > 0


def test_realistic_deadline_summary_uses_catalyst_execution_contract() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=False))
    response = client.post("/api/integrations/convokraft/action", json=_realistic_payload("DeadlineSummary"))

    _assert_execution_contract(response)
    assert set(response.json()["data"]) == {"overdue", "red", "amber", "green"}


def test_realistic_case_detail_uses_catalyst_execution_contract() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=False))
    response = client.post(
        "/api/integrations/convokraft/action",
        json=_realistic_payload("CaseDetail", {"firNumber": "FIR/MAN/0003"}),
    )

    _assert_execution_contract(response)
    assert response.json()["data"]["case"]["fir_number"] == "FIR/MAN/0003"


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


def test_convo_kraft_signature_verification_defaults_to_enabled() -> None:
    assert Settings().convokraft_verify_signature is True


def test_disabled_signature_verification_allows_unsigned_action_processing() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=False, CONVOKRAFT_PUBLIC_KEY=""))
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary"))

    assert response.status_code == 200
    assert response.json()["status"] == "execution"


def test_enabled_signature_verification_rejects_unsigned_request() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=True, CONVOKRAFT_PUBLIC_KEY=""))
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary"))

    assert response.status_code == 401


def test_disabled_signature_verification_does_not_bypass_role_security() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_VERIFY_SIGNATURE=False, CONVOKRAFT_PUBLIC_KEY=""))
    response = client.post("/api/integrations/convokraft/action", json=_payload("case_status_summary", "not-a-role"))

    assert response.status_code == 403


def test_production_webhook_missing_key_with_signature_is_503() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY=""))
    response = client.post(
        "/api/integrations/convokraft/action",
        content=b'{"action":"case_status_summary"}',
        headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": "AAAA"},
    )
    assert response.status_code == 503


def test_literal_newline_key_format_is_supported() -> None:
    private_key = dsa.generate_private_key(key_size=1024)
    pem = private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY=pem.replace("\n", "\\n")))
    body = __import__("json").dumps(_payload("case_status_summary"), separators=(",", ":")).encode()
    signature = __import__("base64").b64encode(private_key.sign(body, hashes.SHA256())).decode()
    response = client.post("/api/integrations/convokraft/action", content=body, headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": signature})
    assert response.status_code == 200


def test_valid_signed_request_returns_case_summary() -> None:
    private_key = dsa.generate_private_key(key_size=1024)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY=public_key))
    body = __import__("json").dumps(_payload("case_status_summary"), separators=(",", ":")).encode()
    signature = __import__("base64").b64encode(private_key.sign(body, hashes.SHA256())).decode()

    response = client.post(
        "/api/integrations/convokraft/action",
        content=body,
        headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": signature},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "execution"


def test_base64_der_dsa_public_key_is_supported() -> None:
    private_key = dsa.generate_private_key(key_size=1024)
    der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY=__import__("base64").b64encode(der).decode()))
    body = __import__("json").dumps(_payload("case_status_summary"), separators=(",", ":")).encode()
    signature = __import__("base64").b64encode(private_key.sign(body, hashes.SHA256())).decode()

    response = client.post(
        "/api/integrations/convokraft/action",
        content=body,
        headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": signature},
    )

    assert response.status_code == 200


def test_malformed_public_key_is_configuration_error() -> None:
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY="not-a-pem-key"))
    response = client.post(
        "/api/integrations/convokraft/action",
        content=b'{"action":"case_status_summary"}',
        headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": "AAAA"},
    )
    assert response.status_code == 503


def test_unavailable_crypto_is_configuration_error(monkeypatch) -> None:
    from backend.app.api import convokraft_routes

    original = convokraft_routes._verify_signature
    monkeypatch.setattr(convokraft_routes, "_verify_signature", lambda *_args: (_ for _ in ()).throw(convokraft_routes.ConvoKraftCryptoUnavailable()))
    client = _client(Settings(ENVIRONMENT="production", CONVOKRAFT_PUBLIC_KEY="configured"))
    response = client.post(
        "/api/integrations/convokraft/action",
        content=b'{"action":"case_status_summary"}',
        headers={"content-type": "application/json", "X-CONVOKRAFT-SIGNATURE": "AAAA"},
    )
    monkeypatch.setattr(convokraft_routes, "_verify_signature", original)
    assert response.status_code == 503
