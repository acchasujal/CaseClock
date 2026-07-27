"""Deterministic ConvoKraft action webhook integration."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.api.dependencies import get_case_service, get_request_id
from backend.app.auth.principal import Principal
from backend.app.config import Settings
from backend.app.services.case_service import CaseService
from shared.contracts.api import UserRole

logger = logging.getLogger(__name__)


class ConvoKraftCryptoUnavailable(RuntimeError):
    """Raised when production signature verification cannot be performed."""


class ConvoKraftKeyConfigurationError(RuntimeError):
    """Raised when the configured ConvoKraft public key is unusable."""


def _execution(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "execution", "message": message, "card": [], "data": data or {}, "broadcast": {}, "trigger": {}, "followup": {}}


def _normalise_public_key(value: str) -> str:
    """Normalize only environment transport escaping; preserve PEM markers/content."""
    return value.replace("\\n", "\n").strip()


def _verify_signature(raw_body: bytes, signature: str, public_key: str) -> bool:
    if not signature or not public_key:
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import dsa
    except ImportError as exc:
        raise ConvoKraftCryptoUnavailable("Signature verification dependency is unavailable") from exc

    try:
        key = serialization.load_pem_public_key(public_key.encode("utf-8"))
        if not isinstance(key, dsa.DSAPublicKey):
            raise ConvoKraftKeyConfigurationError("ConvoKraft public key is not a DSA key")
        key.verify(base64.b64decode(signature, validate=True), raw_body, hashes.SHA256())
        return True
    except InvalidSignature:
        return False
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ConvoKraftKeyConfigurationError("ConvoKraft public key or signature is malformed") from exc


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
        if settings.is_production:
            signature = request.headers.get("X-CONVOKRAFT-SIGNATURE", "")
            public_key = _normalise_public_key(settings.convokraft_public_key)
            logger.info(
                "ConvoKraft signature verification requested",
                extra={
                    "request_id": request_id,
                    "category": "signature_verification",
                    "public_key_configured": bool(public_key),
                    "public_key_length": len(public_key),
                    "public_key_pem": public_key.startswith("-----BEGIN PUBLIC KEY-----") and public_key.endswith("-----END PUBLIC KEY-----"),
                },
            )
            if not signature:
                logger.warning("ConvoKraft signature missing", extra={"request_id": request_id, "category": "missing_signature"})
                raise HTTPException(status_code=401, detail="Invalid ConvoKraft signature")
            if not public_key:
                logger.error("ConvoKraft public key missing", extra={"request_id": request_id, "category": "public_key_missing"})
                raise HTTPException(status_code=503, detail="ConvoKraft signature configuration is missing")
            try:
                verified = _verify_signature(raw_body, signature, public_key)
            except ConvoKraftCryptoUnavailable as exc:
                logger.error("ConvoKraft crypto runtime unavailable", extra={"request_id": request_id, "category": "crypto_runtime_unavailable"})
                raise HTTPException(status_code=503, detail="ConvoKraft signature verification is unavailable") from exc
            except ConvoKraftKeyConfigurationError as exc:
                logger.error("ConvoKraft public key configuration invalid", extra={"request_id": request_id, "category": "public_key_invalid"})
                raise HTTPException(status_code=503, detail="ConvoKraft signature configuration is invalid") from exc
            if not verified:
                logger.warning("ConvoKraft signature invalid", extra={"request_id": request_id, "category": "invalid_signature"})
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
