"""tests/test_document_intelligence.py

Unit and integration tests for Catalyst Evidence Document Intelligence endpoints and workflow.
"""

import base64
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.catalyst.document_intelligence import OcrResult, StoredFile
from backend.app.api.dependencies import get_document_service
from backend.app.services.document_service import DocumentService
from backend.app.services.audit_service import AuditService


class TestDocumentProvider:
    def store_file(self, filename, content_type, content):
        return StoredFile("test-file-1", filename, len(content))

    def extract_optical_characters(self, filename, content_type, content):
        return OcrResult(content.decode("utf-8"), 99.0)


def _make_scan_body(content: bytes, filename: str = "scanned_fir.pdf", document_type: str = "fir") -> dict:
    """Build the JSON body for a document scan request with base64-encoded content."""
    return {
        "filename": filename,
        "content_type": "application/pdf",
        "document_type": document_type,
        "file_base64": base64.b64encode(content).decode(),
    }


@pytest.fixture
def repo():
    return InMemoryBackendRepository()


@pytest.fixture
def app(repo):
    application = create_app(repository=repo)
    application.dependency_overrides[get_document_service] = lambda: DocumentService(repo, AuditService(repo), TestDocumentProvider())
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def test_document_scan_valid_file(client):
    """POST /api/v1/cases/{case_id}/documents/scan uploads document and generates candidate clock preview without altering case clock."""
    worklist = client.get("/worklist").json()
    case_id = worklist[0]["id"]

    # 1. Check initial case detail clock
    case_before = client.get(f"/cases/{case_id}?role=IO").json()
    clock_before = case_before["clocks"][0]["clock_type"]

    # 2. Upload FIR file for scanning (JSON + base64 — no python-multipart required)
    dummy_pdf = b"%PDF-1.4 FIR No. FIR/BEN/0099 Police Station: Mysuru Central Offence: Cybercrime Section 66D IT Act"
    response = client.post(
        f"/api/v1/cases/{case_id}/documents/scan",
        headers={"X-Dev-Role": "IO"},
        json=_make_scan_body(dummy_pdf),
    )

    assert response.status_code == 201
    data = response.json()

    assert data["document_id"].startswith("doc-")
    assert data["ocr_status"] == "success"
    assert data["review_status"] == "pending_review"
    assert data["candidate_facts"]["fir_number"] is not None
    assert data["clock_preview"] is not None
    assert data["clock_preview"]["requires_confirmation"] is True

    # 3. VERIFY SAFETY BOUNDARY: Case clock remains UNCHANGED before confirmation
    case_after = client.get(f"/cases/{case_id}?role=IO").json()
    assert case_after["clocks"][0]["clock_type"] == clock_before


def test_document_scan_unsupported_file_type(client):
    """Unsupported MIME types are rejected with 422 Unprocessable Entity."""
    worklist = client.get("/worklist").json()
    case_id = worklist[0]["id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/documents/scan",
        headers={"X-Dev-Role": "IO"},
        json=_make_scan_body(b"binary", filename="malicious.exe"),
    )
    # The content_type defaults to application/pdf in DocumentScanRequest;
    # the service validates the filename extension — .exe is rejected.
    # The document_service checks the content_type field; pass an explicit bad type.
    response2 = client.post(
        f"/api/v1/cases/{case_id}/documents/scan",
        headers={"X-Dev-Role": "IO"},
        json={
            "filename": "malicious.exe",
            "content_type": "application/x-msdownload",
            "document_type": "fir",
            "file_base64": base64.b64encode(b"binary").decode(),
        },
    )
    assert response2.status_code == 422


def test_document_scan_rejects_invalid_base64_and_empty_payload(client):
    case_id = client.get("/worklist").json()[0]["id"]
    body = {"filename": "scan.png", "content_type": "image/png", "document_type": "fir", "file_base64": "%%%"}
    assert client.post(f"/api/v1/cases/{case_id}/documents/scan", headers={"X-Dev-Role": "IO"}, json=body).status_code == 422
    body["file_base64"] = ""
    assert client.post(f"/api/v1/cases/{case_id}/documents/scan", headers={"X-Dev-Role": "IO"}, json=body).status_code == 422


def test_officer_confirmation_updates_clock_deterministically(repo, client):
    """Officer confirmation of candidate facts updates statutory clock and records audit event."""
    worklist = client.get("/worklist").json()
    case_id = worklist[0]["id"]

    # 1. Scan document (JSON + base64)
    dummy_pdf = b"%PDF-1.4 FIR No. FIR/BEN/0099 Police Station: Mysuru Central Offence: Homicide"
    scan_res = client.post(
        f"/api/v1/cases/{case_id}/documents/scan",
        headers={"X-Dev-Role": "IO"},
        json=_make_scan_body(dummy_pdf),
    ).json()

    doc_id = scan_res["document_id"]

    # 2. Confirm candidate facts as serious_offence (90-day investigation limit)
    confirm_res = client.post(
        f"/api/v1/cases/{case_id}/documents/{doc_id}/confirm",
        headers={"X-Dev-Role": "IO"},
        json={
            "fir_number": "FIR/MYS/2026/0099",
            "police_station": "Mysuru Central",
            "offence_category": "serious_offence",
        },
    )

    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()

    assert confirm_data["review_status"] == "confirmed"
    assert confirm_data["updated_clock"]["clock_type"] == "investigation_90_day"

    # 3. Verify case detail reflects updated clock
    case_detail = client.get(f"/cases/{case_id}?role=IO").json()
    assert case_detail["offence_category"] == "serious_offence"

    # 4. Verify audit trail records confirmation
    audit_events = [e for e in repo.audit_events if e.get("event_type") == "document_facts_confirmed"]
    assert len(audit_events) >= 1
    assert audit_events[-1]["metadata"]["document_id"] == doc_id
