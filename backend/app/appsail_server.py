"""AppSail startup entry point for CaseClock backend.

Catalyst AppSail requires a managed-runtime startup via:
    python backend/app/appsail_server.py

The backend listens on the port provided by Catalyst:
    X_ZOHO_CATALYST_LISTEN_PORT  (set by AppSail runtime)

If the env var is not set (local development), falls back to port 8000.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path

# Dependencies are staged inside the exact AppSail source root by predeploy.
app_root = Path(__file__).resolve().parent.parent
vendor_dir = app_root / "vendor"
if vendor_dir.is_dir():
    sys.path.insert(0, str(vendor_dir))

# Add project root and app parent directory to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

app_parent_dir = Path(__file__).resolve().parent.parent
if str(app_parent_dir) not in sys.path:
    sys.path.append(str(app_parent_dir))

# Support absolute 'backend.app' and 'backend.shared' imports in production
import types
backend_mock = types.ModuleType("backend")
sys.modules["backend"] = backend_mock

try:
    import app
    sys.modules["backend.app"] = app
    backend_mock.app = app
except Exception as err:
    logging.warning("Could not alias app module: %s", err)

try:
    import shared
    sys.modules["backend.shared"] = shared
    backend_mock.shared = shared
except Exception as err:
    logging.warning("Could not alias shared module: %s", err)
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _log_crypto_runtime() -> None:
    """Emit safe runtime diagnostics for the signed ConvoKraft integration."""
    logger.info("ConvoKraft crypto runtime python=%s platform=%s machine=%s", sys.version.split()[0], platform.platform(), platform.machine())
    imports = (
        ("cryptography", "import cryptography"),
        ("InvalidSignature", "from cryptography.exceptions import InvalidSignature"),
        ("hashes", "from cryptography.hazmat.primitives import hashes"),
        ("serialization", "from cryptography.hazmat.primitives import serialization"),
        ("dsa", "from cryptography.hazmat.primitives.asymmetric import dsa"),
    )
    for stage, statement in imports:
        try:
            namespace: dict[str, object] = {}
            exec(statement, namespace)
            module = namespace.get("cryptography")
            logger.info("ConvoKraft crypto_init stage=%s result=success%s", stage, f" version={getattr(module, '__version__', 'unknown')} path={getattr(module, '__file__', 'unknown')}" if stage == "cryptography" else "")
        except Exception as exc:
            logger.error("ConvoKraft crypto_init stage=%s result=failure exception_type=%s exception=%s", stage, type(exc).__name__, str(exc)[:160])


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
    _log_crypto_runtime()
    app_module = "app.main:app"
    logger.info("Starting CaseClock backend on port %d using module %s", port, app_module)
    uvicorn.run(
        app_module,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
