"""Frontend-compatible backend API routes for core CaseClock workflows.

Route handlers are thin HTTP adapters: they validate inputs, call the
repository, translate domain exceptions to HTTP responses, and return
contract types.  No business logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import get_repository, get_request_id
from backend.app.api.errors import NotFoundError
from backend.app.db.in_memory import InMemoryBackendRepository
from shared.contracts.api import (
    CaseDetailResponse,
    CaseSummaryResponse,
    CopilotQueryRequest,
    CopilotQueryResponse,
    DependencyResponse,
    DependencyStatus,
    EscalationResponse,
)


class DependencyUpdateRequest(BaseModel):
    status: DependencyStatus


def create_core_router() -> APIRouter:
    """Return the core API router.

    Phase 1: routes depend on ``get_repository`` from app.state so that tests
    can supply an isolated in-memory repository.
    """
    router = APIRouter(tags=["backend-core"])

    @router.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe.  Returns service name and version only."""
        from backend.app.config import get_settings

        cfg = get_settings()
        return {
            "status": "ok",
            "service": "caseclock-backend",
            "version": cfg.app_version,
        }

    @router.get("/worklist", response_model=list[CaseSummaryResponse])
    def worklist(
        role: str = Query("IO", pattern="^(IO|SHO|SP)$"),
        repo: InMemoryBackendRepository = Depends(get_repository),
        request_id: str = Depends(get_request_id),
    ) -> list[CaseSummaryResponse]:
        """Risk-ranked visible cases.

        Role is accepted as a query parameter in Phase 1 (no real auth).
        Phase 3 will derive role from the verified Catalyst token and ignore
        the query parameter entirely.
        """
        return repo.list_worklist(role=role)

    @router.get("/cases/{case_id}", response_model=CaseDetailResponse)
    def case_detail(
        case_id: str,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> CaseDetailResponse:
        """Full case object for the Case Detail screen."""
        result = repo.get_case_detail(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/cases/{case_id}/network")
    def case_network(
        case_id: str,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> dict:
        """React Flow graph around a case.  Depth-1 BFS; max 18 nodes."""
        result = repo.case_network(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/escalations", response_model=list[EscalationResponse])
    def escalations(
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[EscalationResponse]:
        """Visible unresolved/resolved escalation events."""
        return repo.list_escalations()

    @router.get("/audit")
    def audit_events(
        limit: int = Query(100, ge=1, le=500),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[dict]:
        """Append-only audit log.  SHO/SP only in Phase 3."""
        return repo.list_audit_events(limit=limit)

    @router.patch("/deps/{dependency_id}", response_model=DependencyResponse)
    def update_dependency(
        dependency_id: str,
        request: DependencyUpdateRequest,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> DependencyResponse:
        """Update dependency status.  Validates state transition; writes audit."""
        result = repo.update_dependency(dependency_id, request.status)
        if result is None:
            raise HTTPException(status_code=404, detail="Dependency not found")
        return result

    @router.post("/copilot/query", response_model=CopilotQueryResponse)
    def copilot_query(
        request: CopilotQueryRequest,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> CopilotQueryResponse:
        """Deterministic copilot query.  Refuses prohibited inferences."""
        return repo.copilot_query(request.query, request.case_id)

    return router
