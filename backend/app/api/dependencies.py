"""backend/app/api/dependencies.py

FastAPI dependency providers for shared application objects.

In Phase 1, these yield the in-memory adapter and an anonymous principal.
In Phase 2/3, these are replaced with Catalyst Data Store and Auth verifier
dependencies — without changing any route signature.

Pattern:
    Each route declares what it needs:
        repo: InMemoryBackendRepository = Depends(get_repository)
        principal: Principal = Depends(get_principal)
    This file owns the wiring, not the route.
"""

from __future__ import annotations

from fastapi import Depends, Request

from backend.app.auth.principal import Principal
from backend.app.auth.verifier import make_verifier
from backend.app.config import Settings, get_settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.case_service import CaseService
from backend.app.services.copilot_service import CopilotService


def get_settings_dep() -> Settings:
    """Provide application settings as a FastAPI dependency.

    Wraps the cached `get_settings()` so routes can type-hint:
        settings: Settings = Depends(get_settings_dep)
    """
    return get_settings()


def get_repository(request: Request) -> InMemoryBackendRepository:
    """Return the shared InMemoryBackendRepository stored in app.state.

    The repository instance is attached to ``app.state.repository`` in
    ``create_app()`` so it is shared across all requests without needing
    a module-level singleton.

    Phase 2 replaces this dependency to return a Catalyst-backed repository
    without touching route handlers.
    """
    return request.app.state.repository  # type: ignore[no-any-return]


async def get_principal(request: Request) -> Principal:
    """Return the verified Principal for the current request.

    Phase 1: DevelopmentVerifier reads role from X-Dev-Role header.
    Phase 3: CatalystAuthVerifier verifies the Catalyst JWT.

    Routes that need to make authorization decisions:
        principal: Principal = Depends(get_principal)
    """
    settings: Settings = request.app.state.settings
    verifier = make_verifier(settings)
    return await verifier.verify(request)


def get_request_id(request: Request) -> str:
    """Return the correlation ID set by RequestIDMiddleware.

    Routes that need to attach the request ID to audit records or log lines
    can declare:
        request_id: str = Depends(get_request_id)
    """
    return getattr(request.state, "request_id", "unknown")


def get_audit_service(
    repo: InMemoryBackendRepository = Depends(get_repository)
) -> AuditService:
    """Provide AuditService instance."""
    return AuditService(repo)


def get_case_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> CaseService:
    """Provide CaseService instance."""
    return CaseService(repo, audit_svc)


def get_copilot_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> CopilotService:
    """Provide CopilotService instance."""
    return CopilotService(repo, audit_svc)
