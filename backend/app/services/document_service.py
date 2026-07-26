"""Truthful document processing: real File Store + real Zia OCR only."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.app.catalyst.document_intelligence import CatalystDocumentProvider, DocumentProviderError
from backend.app.core.clock.engine import ClockEngine
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.constants.clock_types import get_clock_rule
from shared.contracts.api import (
    CandidateFactField, ClockInstanceResponse, ClockPreviewResponse, ClockStatus,
    DocumentCandidateFacts, DocumentConfirmRequest, DocumentConfirmResponse,
    DocumentScanResponse,
)

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png", "image/tiff", "image/bmp"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


class DocumentService:
    def __init__(self, repository: Any, audit_service: AuditService, provider: CatalystDocumentProvider | None = None) -> None:
        self._repo, self._audit, self._provider = repository, audit_service, provider
        self._clock_engine = ClockEngine(getattr(repository, "reference_time", None))
        self._documents: dict[str, dict[str, Any]] = getattr(repository, "documents", {})
        if not hasattr(repository, "documents"):
            repository.documents = self._documents

    def scan_document(self, case_id: str, file_bytes: bytes, filename: str, content_type: str, document_type: str = "fir") -> DocumentScanResponse:
        if not file_bytes:
            raise ValueError("File payload is empty.")
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError("File size exceeds 20 MB limit.")
        mime = content_type.lower().split(";", 1)[0].strip()
        filename = self._safe_filename(filename)
        if mime not in ALLOWED_MIME_TYPES or not filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
            raise ValueError("Unsupported file format. Allowed: PDF, JPEG, PNG, TIFF, BMP.")

        try:
            provider = self._provider or CatalystDocumentProvider.from_env()
        except Exception as exc:
            raise DocumentProviderError("Catalyst document provider is unavailable.") from exc
        stored = provider.store_file(filename, mime, file_bytes)
        ocr = provider.extract_optical_characters(filename, mime, file_bytes)
        document_id, uploaded_at = f"doc-{uuid4().hex[:10]}", datetime.now(timezone.utc).isoformat()
        facts = self._extract_candidate_facts(ocr.text)
        preview = self._generate_clock_preview(case_id, facts)
        record = {
            "document_id": document_id, "case_id": case_id, "document_type": document_type,
            "original_filename": filename, "storage_reference": stored.file_id,
            "catalyst_file_id": stored.file_id, "mime_type": mime, "size_bytes": stored.file_size,
            "uploaded_at": uploaded_at, "ocr_status": "success", "ocr_text": ocr.text,
            "ocr_confidence": ocr.confidence, "candidate_facts": facts.model_dump(),
            "review_status": "pending_review",
        }
        self._documents[document_id] = record
        save_state = getattr(self._repo, "_save_state", None)
        if callable(save_state):
            save_state()
        self._audit.record(AuditEventType.DOCUMENT_UPLOADED, actor_id="system-officer", case_id=case_id, document_id=document_id, catalyst_file_id=stored.file_id, filename=filename, size_bytes=stored.file_size)
        self._audit.record(AuditEventType.DOCUMENT_OCR_COMPLETED, actor_id="system-officer", case_id=case_id, document_id=document_id, ocr_status="success", ocr_confidence=ocr.confidence)
        return DocumentScanResponse(document_id=document_id, case_id=case_id, document_type=document_type, original_filename=filename, storage_reference=stored.file_id, uploaded_at=uploaded_at, ocr_status="success", ocr_text=ocr.text, ocr_confidence=ocr.confidence, candidate_facts=facts, clock_preview=preview, review_status="pending_review")

    @staticmethod
    def _safe_filename(filename: str) -> str:
        value = filename.replace("\\", "/").split("/")[-1].strip()
        if not value or value in {".", ".."} or "\x00" in value:
            raise ValueError("Invalid filename.")
        return re.sub(r"[^A-Za-z0-9._-]", "_", value)[:180]

    def _extract_candidate_facts(self, text: str) -> DocumentCandidateFacts:
        fir = re.search(r"FIR\s*(?:No\.?|NUMBER)?[:\s]*([A-Z0-9/-]+)", text, re.I)
        station = re.search(r"(?:P\.?S\.?|Police Station)[:\s]*([A-Za-z ]+)", text, re.I)
        date = re.search(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", text)
        sections = [f"BNS {item}" for item in re.findall(r"(?:BNS|IPC|Section|Sec\.?)\s*(\d+(?:\(\d+\))?)", text, re.I)]
        upper = text.upper()
        category = "fraud" if any(x in upper for x in ("CYBER", "IT ACT", "FRAUD")) else "serious_offence" if any(x in upper for x in ("MURDER", "HOMICIDE")) else "robbery" if any(x in upper for x in ("DACOITY", "ROBBERY")) else "narcotics" if any(x in upper for x in ("NARCOTICS", "NDPS")) else "theft"
        return DocumentCandidateFacts(
            fir_number=CandidateFactField(value=fir.group(1), source_text=fir.group(0)) if fir else None,
            police_station=CandidateFactField(value=station.group(1).strip(), source_text=station.group(0)) if station else None,
            fir_registration_date=CandidateFactField(value=date.group(0), source_text=date.group(0)) if date else None,
            offence_sections=sections, offence_category=CandidateFactField(value=category, source_text=category),
        )

    def _generate_clock_preview(self, case_id: str, facts: DocumentCandidateFacts) -> ClockPreviewResponse:
        rule = get_clock_rule(facts.offence_category.value if facts.offence_category else "theft")
        now = getattr(self._repo, "reference_time", None) or datetime.now(timezone.utc)
        if now.tzinfo is None: now = now.replace(tzinfo=timezone.utc)
        deadline = now + timedelta(days=rule.duration_days)
        remaining = (deadline.date() - now.date()).days
        status = ClockStatus.OVERDUE if remaining < 0 else ClockStatus.RED if remaining < 7 else ClockStatus.AMBER if remaining <= 14 else ClockStatus.GREEN
        return ClockPreviewResponse(applicable_rule=rule.clock_type.value, duration_days=rule.duration_days, calculated_deadline=deadline.strftime("%Y-%m-%d"), days_remaining=remaining, predicted_status=status, bnss_reference=rule.bnss_reference, requires_confirmation=True)

    def confirm_document_facts(self, case_id: str, document_id: str, request: DocumentConfirmRequest) -> DocumentConfirmResponse:
        doc = self._documents.get(document_id)
        if not doc or doc.get("case_id") != case_id: raise ValueError(f"Document '{document_id}' not found for case '{case_id}'.")
        if doc.get("review_status") == "confirmed": return DocumentConfirmResponse.model_validate(doc["confirmation_response"])
        case = getattr(self._repo, "nodes", {}).get(case_id, {})
        if request.offence_category: case["offence_category"] = request.offence_category
        if request.fir_number: case["fir_number"] = request.fir_number
        if request.police_station: case["station_name"] = request.police_station
        updated = ClockInstanceResponse.model_validate(self._clock_engine.from_case(case_id, case).model_dump())
        doc["review_status"], doc["confirmed_facts"] = "confirmed", request.model_dump()
        save_state = getattr(self._repo, "_save_state", None)
        if callable(save_state):
            save_state()
        self._audit.record(AuditEventType.DOCUMENT_FACTS_CONFIRMED, actor_id="system-officer", case_id=case_id, document_id=document_id)
        response = DocumentConfirmResponse(document_id=document_id, case_id=case_id, updated_clock=updated, message="Officer confirmation received. Statutory investigation clock updated successfully.")
        doc["confirmation_response"] = response.model_dump(mode="json")
        return response
