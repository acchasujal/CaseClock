"""Frontend-compatible backend API routes for core CaseClock workflows.

Route handlers are thin HTTP adapters: they validate inputs, call the
repository, translate domain exceptions to HTTP responses, and return
contract types.  No business logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_request_id,
    get_principal,
    get_case_service,
    get_copilot_service,
    get_audit_service,
)
from backend.app.auth.principal import Principal
from backend.app.services.case_service import CaseService
from backend.app.services.copilot_service import CopilotService
from backend.app.services.audit_service import AuditService
from shared.contracts.api import (
    CaseDetailResponse,
    CaseSummaryResponse,
    CopilotQueryRequest,
    CopilotQueryResponse,
    DependencyResponse,
    DependencyStatus,
    EscalationResponse,
    DistrictRollupResponse,
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
        role: str | None = Query(None, pattern="^(IO|SHO|SP)$"),
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> list[CaseSummaryResponse]:
        """Risk-ranked visible cases."""
        return case_svc.list_worklist(principal=principal, request_id=request_id)

    @router.get("/cases/{case_id}", response_model=CaseDetailResponse)
    def case_detail(
        case_id: str,
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> CaseDetailResponse:
        """Full case object for the Case Detail screen."""
        result = case_svc.get_case_detail(case_id, principal=principal, request_id=request_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/cases/{case_id}/network")
    def case_network(
        case_id: str,
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> dict:
        """React Flow graph around a case.  Depth-1 BFS; max 18 nodes."""
        result = case_svc.get_case_network(case_id, principal=principal, request_id=request_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/escalations", response_model=list[EscalationResponse])
    def escalations(
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> list[EscalationResponse]:
        """Visible unresolved/resolved escalation events."""
        return case_svc.list_escalations(principal=principal, request_id=request_id)

    @router.get("/audit")
    def audit_events(
        limit: int = Query(100, ge=1, le=500),
        principal: Principal = Depends(get_principal),
        audit_svc: AuditService = Depends(get_audit_service),
    ) -> list[dict]:
        """Append-only audit log.  SHO/SP only."""
        if not principal.can_view_audit_log():
            from backend.app.api.errors import ForbiddenError
            raise ForbiddenError("Audit log access is restricted to SHO/SP roles.")
        return audit_svc.list_events(limit=limit)

    @router.patch("/deps/{dependency_id}", response_model=DependencyResponse)
    def update_dependency(
        dependency_id: str,
        request: DependencyUpdateRequest,
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> DependencyResponse:
        """Update dependency status.  Validates state transition; writes audit."""
        result = case_svc.update_dependency(
            dependency_id, request.status, principal=principal, request_id=request_id
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Dependency not found")
        return result

    @router.post("/copilot/query", response_model=CopilotQueryResponse)
    def copilot_query(
        request: CopilotQueryRequest,
        principal: Principal = Depends(get_principal),
        copilot_svc: CopilotService = Depends(get_copilot_service),
        request_id: str = Depends(get_request_id),
    ) -> CopilotQueryResponse:
        """Deterministic copilot query.  Refuses prohibited inferences."""
        return copilot_svc.handle_query(request, principal=principal, request_id=request_id)

    @router.get("/rollup/{district}", response_model=DistrictRollupResponse)
    def district_rollup(
        district: str,
        principal: Principal = Depends(get_principal),
        case_svc: CaseService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> DistrictRollupResponse:
        """Exception-only operational overview of police stations in the district."""
        if not principal.can_access_sp_features() and not principal.can_access_sho_features():
            from backend.app.api.errors import ForbiddenError
            raise ForbiddenError("District rollup access is restricted to supervisor roles.")
        return case_svc.get_district_rollup(district, principal=principal, request_id=request_id)

    return router
