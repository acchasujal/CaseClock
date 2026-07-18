"""Frontend-compatible backend API routes for Dev 1 core workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

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


def create_core_router(repository: InMemoryBackendRepository) -> APIRouter:
    router = APIRouter(tags=["backend-core"])

    def get_repository() -> InMemoryBackendRepository:
        return repository

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "caseclock-backend"}

    @router.get("/worklist", response_model=list[CaseSummaryResponse])
    def worklist(
        role: str = Query("IO", pattern="^(IO|SHO|SP)$"),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[CaseSummaryResponse]:
        return repo.list_worklist(role=role)

    @router.get("/cases/{case_id}", response_model=CaseDetailResponse)
    def case_detail(
        case_id: str,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> CaseDetailResponse:
        result = repo.get_case_detail(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/cases/{case_id}/network")
    def case_network(
        case_id: str,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> dict:
        result = repo.case_network(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return result

    @router.get("/escalations", response_model=list[EscalationResponse])
    def escalations(
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[EscalationResponse]:
        return repo.list_escalations()

    @router.get("/audit")
    def audit_events(
        limit: int = Query(100, ge=1, le=500),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[dict]:
        return repo.list_audit_events(limit=limit)

    @router.patch("/deps/{dependency_id}", response_model=DependencyResponse)
    def update_dependency(
        dependency_id: str,
        request: DependencyUpdateRequest,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> DependencyResponse:
        result = repo.update_dependency(dependency_id, request.status)
        if result is None:
            raise HTTPException(status_code=404, detail="Dependency not found")
        return result

    @router.post("/copilot/query", response_model=CopilotQueryResponse)
    def copilot_query(
        request: CopilotQueryRequest,
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> CopilotQueryResponse:
        return repo.copilot_query(request.query, request.case_id)

    return router
