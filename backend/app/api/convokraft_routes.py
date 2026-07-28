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


def _action_key(value: str) -> str:
    """Normalize Catalyst action IDs and human-readable action names."""
    return "".join(character for character in value.casefold() if character.isalnum())


def _action_response(action_name: str, response: dict[str, Any]) -> dict[str, Any]:
    logger.info(
        "ConvoKraft action response action=%s response_type=%s top_level_keys=%s http_status=%d",
        action_name,
        response.get("status", ""),
        sorted(response.keys()),
        200,
        extra={"category": "action_response"},
    )
    logger.info(
        "ConvoKraft FULL RESPONSE:\n%s",
        json.dumps(response, indent=2, default=str),
        extra={
            "category": "action_response_debug",
            "http_status": 200,
            "response_type": response.get("status"),
            "status_value": response.get("status"),
            "message_type": type(response.get("message")).__name__,
            "message_value": response.get("message"),
            "card_type": type(response.get("card")).__name__,
            "card_value": response.get("card"),
            "data_type": type(response.get("data")).__name__,
            "data_value": response.get("data"),
            "broadcast_type": type(response.get("broadcast")).__name__,
            "broadcast_value": response.get("broadcast"),
            "followup_type": type(response.get("followup")).__name__,
            "followup_value": response.get("followup"),
            "trigger_type": type(response.get("trigger")).__name__,
            "trigger_value": response.get("trigger"),
        },
    )
    return response


def _normalise_public_key(value: str) -> str:
    """Normalize only environment transport escaping; preserve PEM markers/content."""
    return value.replace("\\n", "\n").strip()


def _public_key_representation(value: str) -> str:
    """Classify key transport without logging key material."""
    normalized = _normalise_public_key(value)
    if not normalized:
        return "missing"
    if normalized.startswith("-----BEGIN") and normalized.endswith("-----"):
        return "pem"
    try:
        decoded = base64.b64decode("".join(normalized.split()), validate=True)
    except (ValueError, binascii.Error):
        return "unrecognized"
    if decoded.startswith(b"-----BEGIN"):
        return "base64_pem"
    return "base64_der"


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
        normalized_key = _normalise_public_key(public_key)
        if normalized_key.startswith("-----BEGIN"):
            key = serialization.load_pem_public_key(normalized_key.encode("utf-8"))
        else:
            key_bytes = base64.b64decode("".join(normalized_key.split()), validate=True)
            if key_bytes.startswith(b"-----BEGIN"):
                key = serialization.load_pem_public_key(key_bytes)
            else:
                key = serialization.load_der_public_key(key_bytes)
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
    if settings.is_production and settings.convokraft_verify_signature and not settings.convokraft_public_key:
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
        request_headers = {
            key: value
            for key, value in request.headers.items()
            if key.casefold() != "authorization"
        }
        request_payload: Any = None
        try:
            request_payload = json.loads(raw_body)
            request_body_log = json.dumps(request_payload, indent=2, default=str)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            request_body_log = raw_body.decode("utf-8", errors="replace")
        logger.info(
            "\n================ FULL CONVOKRAFT REQUEST ================\n%s\n================ END REQUEST ================",
            request_body_log,
            extra={
                "category": "full_convokraft_request",
                "top_level_keys": sorted(request_payload.keys()) if isinstance(request_payload, dict) else [],
                "request_path": request.url.path,
                "request_method": request.method,
                "content_type": request.headers.get("content-type", ""),
                "user_agent": request.headers.get("user-agent", ""),
                "request_headers": request_headers,
                "action_exists": isinstance(request_payload, dict) and "action" in request_payload,
                "skill_exists": isinstance(request_payload, dict) and "skill" in request_payload,
                "todo_exists": isinstance(request_payload, dict) and "todo" in request_payload,
                "client_data_exists": isinstance(request_payload, dict) and "clientData" in request_payload,
                "session_data_exists": isinstance(request_payload, dict) and "sessionData" in request_payload,
            },
        )
        if settings.is_production and settings.convokraft_verify_signature:
            signature = request.headers.get("X-CONVOKRAFT-SIGNATURE", "")
            public_key = _normalise_public_key(settings.convokraft_public_key)
            logger.info(
                "ConvoKraft signature verification requested source=CONVOKRAFT_PUBLIC_KEY "
                "configured=%s length=%d representation=%s",
                bool(public_key),
                len(public_key),
                _public_key_representation(public_key),
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
        elif settings.is_production:
            logger.warning(
                "ConvoKraft signature verification disabled by configuration",
                extra={"request_id": request_id, "category": "signature_verification_disabled"},
            )
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Malformed ConvoKraft payload") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Malformed ConvoKraft payload")

        principal = _principal_from_payload(payload, settings)
        action_name = str(payload.get("action") or "").strip()
        action_key = _action_key(action_name)
        params = payload.get("params") or {}
        logger.info(
            "ConvoKraft action received action=%s top_level_keys=%s parameter_names=%s",
            action_name,
            sorted(str(key) for key in payload.keys()),
            sorted(str(key) for key in params.keys()) if isinstance(params, dict) else [],
            extra={"category": "action_request"},
        )
        worklist = case_svc.list_worklist(principal=principal, request_id=request_id)
        statuses = {status: sum(item.clock.status.value == status for item in worklist) for status in ("overdue", "red", "amber", "green")}

        if action_key in {"casestatussummary"}:
            message = f"{len(worklist)} active cases are currently in the {principal.role.value} worklist: {statuses['overdue']} overdue, {statuses['red']} red-risk, {statuses['amber']} amber and {statuses['green']} green."
            return _action_response(action_name, _execution(message, {"active_case_count": len(worklist), **statuses}))
        if action_key in {"urgentcases"}:
            urgent = [item for item in worklist if item.clock.status.value in {"overdue", "red"}]
            names = ", ".join(item.fir_number for item in urgent[:10]) or "None"
            return _action_response(action_name, _execution(f"{len(urgent)} cases require immediate attention: {names}.", {"count": len(urgent), "cases": [item.fir_number for item in urgent]}))
        if action_key in {"deadlinesummary"}:
            return _action_response(action_name, _execution(f"Deadline summary: {statuses['overdue']} overdue, {statuses['red']} red-risk, {statuses['amber']} amber and {statuses['green']} green.", statuses))
        if action_key in {"casedetailsummary", "casedetail"}:
            normalized_params = {_action_key(str(key)): value for key, value in params.items()} if isinstance(params, dict) else {}
            case_id = str(normalized_params.get("caseid") or normalized_params.get("firnumber") or "")
            if not case_id:
                return _action_response(action_name, _execution("Please provide a case ID or FIR number."))
            lookup_id = case_id
            if normalized_params.get("firnumber"):
                matching_case = next(
                    (item for item in worklist if item.fir_number.casefold() == case_id.casefold()),
                    None,
                )
                lookup_id = matching_case.id if matching_case else case_id
            detail = case_svc.get_case_detail(lookup_id, principal=principal, request_id=request_id)
            if detail is None:
                return _action_response(action_name, _execution(f"I could not find case {case_id}."))
            return _action_response(action_name, _execution(f"{detail.fir_number} is recorded at {detail.station_name} with {len(detail.dependencies)} dependencies and {len(detail.clocks)} statutory clocks.", {"case": detail.model_dump()}))
        return _action_response(action_name, _execution("I do not support that CaseClock action yet."))

    return router
