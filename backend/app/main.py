"""FastAPI entry point for the CaseClock backend prototype."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.core_routes import create_core_router
from backend.app.api.graph_routes import create_graph_router
from backend.app.db.in_memory import InMemoryBackendRepository


def create_app(repository: InMemoryBackendRepository | None = None) -> FastAPI:
    repository = repository or InMemoryBackendRepository(
        state_path=Path("artifacts/runtime_state/backend_state.json")
    )
    app = FastAPI(
        title="CaseClock Backend",
        version="0.1.0",
        description="Deterministic legal-clock-aware investigation backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_core_router(repository))
    app.include_router(create_graph_router(repository.graph_repository), prefix="/api/v1")
    return app


app = create_app()
