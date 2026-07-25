"""backend/app/api/cron_routes.py

Internal administrative job endpoints for Zoho Catalyst Pre-defined Cron.

Machine-to-machine authentication is enforced via X-CaseClock-Cron-Secret header
and fails closed if unconfigured or secret is mismatched.
"""

from __future__ import annotations

import hmac
from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.api.dependencies import get_cron_service
from backend.app.config import Settings, get_settings
from backend.app.services.cron_service import CronService


def create_cron_router() -> APIRouter:
    """Return router for internal scheduled job endpoints."""
    router = APIRouter(prefix="/internal/jobs", tags=["internal-cron"])

    @router.post("/deadline-sweep")
    def deadline_sweep(
        request: Request,
        cron_svc: CronService = Depends(get_cron_service),
    ) -> dict:
        """Scheduled cron endpoint to trigger autonomous statutory clock recalculations.

        Requires machine-to-machine authentication via header:
            X-CaseClock-Cron-Secret: <CRON_SECRET>
        or:
            Authorization: Bearer <CRON_SECRET>
        """
        settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
        configured_secret = settings.cron_secret.strip()
        if not configured_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cron authentication failed: CRON_SECRET is not configured on the server.",
            )

        incoming_secret = request.headers.get("X-CaseClock-Cron-Secret")
        if not incoming_secret:
            auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                incoming_secret = auth_header[7:].strip()

        if not incoming_secret or not hmac.compare_digest(incoming_secret, configured_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cron authentication failed: Invalid or missing cron secret.",
            )

        summary = cron_svc.run_deadline_sweep()
        return summary

    return router
