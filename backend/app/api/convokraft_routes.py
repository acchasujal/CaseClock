"""Deterministic ConvoKraft action webhook integration."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.api.dependencies import get_case_service, get_request_id
from backend.app.auth.principal import Principal
from backend.app.config import Settings
from backend.app.services.case_service import CaseService
from shared.contracts.api import UserRole


def _execution(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "execution", "message": message, "card": [], "data": data or {}, "broadcast": {}, "trigger": {}, "followup": {}}


def _verify_signature(raw_body: bytes, signature: str, public_key: str) -> bool:
    if not signature or not public_key:
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import dsa

        key = serialization.load_pem_public_key(public_key.encode("utf-8"))
        if not isinstance(key, dsa.DSAPublicKey):
            return False
        key.verify(base64.b64decode(signature, validate=True), raw_body, hashes.SHA256())
        return True
    except (ImportError, InvalidSignature, ValueError, TypeError, binascii.Error):
        return False


def _principal_from_payload(payload: dict[str, Any], settings: Settings) -> Principal:
    client_data = payload.get("clientData") or {}
    try:
        role = UserRole(str(client_data.get("role") or "IO").upper())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Unsupported CaseClock role") from exc
    if settings.is_production and not settings.convokraft_public_key:
        raise HTTPException(status_code=503, detail="ConvoKraft signature verification is not configured")
    user = payload.get("user") or {}
    return Principal(
        user_id=str(user.get("id") or user.get("zuid") or "convokraft-user"),
        email=str(user.get("email") or "convokraft@caseclock.internal"),
        role=role,
        is_anonymous=True,
    )


def create_convokraft_router() -> APIRouter:
    router = APIRouter(prefix="/api/integrations/convokraft", tags=["convokraft"])

    @router.post("/action")
    async def action(
        request: Request,
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> dict[str, Any]:
        raw_body = await request.body()
        settings: Settings = request.app.state.settings
        if settings.is_production and not _verify_signature(raw_body, request.headers.get("X-CONVOKRAFT-SIGNATURE", ""), settings.convokraft_public_key):
            raise HTTPException(status_code=401, detail="Invalid ConvoKraft signature")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Malformed ConvoKraft payload") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Malformed ConvoKraft payload")

        principal = _principal_from_payload(payload, settings)
        action_name = str(payload.get("action") or "").strip().lower()
        worklist = case_svc.list_worklist(principal=principal, request_id=request_id)
        statuses = {status: sum(item.clock.status.value == status for item in worklist) for status in ("overdue", "red", "amber", "green")}

        if action_name == "case_status_summary":
            message = f"{len(worklist)} active cases are currently in the {principal.role.value} worklist: {statuses['overdue']} overdue, {statuses['red']} red-risk, {statuses['amber']} amber and {statuses['green']} green."
            return _execution(message, {"active_case_count": len(worklist), **statuses})
        if action_name == "urgent_cases":
            urgent = [item for item in worklist if item.clock.status.value in {"overdue", "red"}]
            names = ", ".join(item.fir_number for item in urgent[:10]) or "None"
            return _execution(f"{len(urgent)} cases require immediate attention: {names}.", {"count": len(urgent), "cases": [item.fir_number for item in urgent]})
        if action_name == "deadline_summary":
            return _execution(f"Deadline summary: {statuses['overdue']} overdue, {statuses['red']} red-risk, {statuses['amber']} amber and {statuses['green']} green.", statuses)
        if action_name == "case_detail_summary":
            params = payload.get("params") or {}
            case_id = str(params.get("case_id") or params.get("fir_number") or "")
            if not case_id:
                return _execution("Please provide a case ID or FIR number.")
            detail = case_svc.get_case_detail(case_id, principal=principal, request_id=request_id)
            if detail is None:
                return _execution(f"I could not find case {case_id}.")
            return _execution(f"{detail.fir_number} is recorded at {detail.station_name} with {len(detail.dependencies)} dependencies and {len(detail.clocks)} statutory clocks.", {"case": detail.model_dump()})
        return _execution("I do not support that CaseClock action yet.")

    return router
