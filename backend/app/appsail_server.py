"""AppSail startup entry point for CaseClock backend.

Catalyst AppSail requires a managed-runtime startup via:
    python backend/app/appsail_server.py

The backend listens on the port provided by Catalyst:
    X_ZOHO_CATALYST_LISTEN_PORT  (set by AppSail runtime)

If the env var is not set (local development), falls back to port 8000.

## Deployment requirements (Phase 7)

1. This file must be the AppSail startup command target.
2. CORS_ORIGINS must be set to the deployed Catalyst Slate URL in AppSail
   environment configuration (not here in code).
3. ENVIRONMENT=production must be set in AppSail environment variables.
4. STATE_PATH must be set (or left empty to disable in-memory persistence).
5. Catalyst Auth credentials (Phase 3) must be set before deploying.

## Command for AppSail startup command field

    python backend/app/appsail_server.py
"""

from __future__ import annotations

import logging
import os

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _get_port() -> int:
    """Get the port to listen on.

    AppSail provides X_ZOHO_CATALYST_LISTEN_PORT; fall back to 8000 locally.
    """
    port_env = os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT")
    if port_env:
        try:
            return int(port_env)
        except ValueError:
            logger.warning("Invalid X_ZOHO_CATALYST_LISTEN_PORT=%r; falling back to 8000", port_env)
    return 8000


if __name__ == "__main__":
    port = _get_port()
    logger.info("Starting CaseClock backend on port %d", port)
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        # AppSail handles TLS termination; backend runs HTTP internally.
        # Do not set ssl_certfile/ssl_keyfile here.
    )
