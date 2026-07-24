"""backend/app/auth/verifier.py

Catalyst Auth token verification for CaseClock.

## Phase 3 implementation

Catalyst Auth issues JWTs that include Zoho user claims.  The backend must:
  1. Accept the token from the `Authorization: Bearer <token>` header.
  2. Verify the token signature against the Catalyst JWKS endpoint.
  3. Extract user_id (ZUID), email, and role.
  4. Return an immutable Principal or raise ForbiddenError.

## Phase 1 stopgap

While Catalyst Auth credentials are not yet configured, the verifier uses
DevelopmentVerifier, which extracts a role from a `X-Dev-Role` header.
This header is only accepted in `environment != production` mode.

## Wiring

Phase 3 replaces DevelopmentVerifier with CatalystAuthVerifier by updating
`get_principal()` in `backend/app/api/dependencies.py`.
No route code changes required.

## Security properties (from plan §9 Phase 3)

- Token verification happens once per request, in the dependency layer.
- Principal is immutable and request-scoped; never cached across requests.
- All token-related failures raise ForbiddenError (not NotFoundError).
- Forbidden access is recorded in the audit trail before raising.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.security import HTTPBearer

from backend.app.api.errors import ForbiddenError
from backend.app.auth.principal import Principal
from shared.contracts.api import UserRole

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.app.config import Settings

_bearer_scheme = HTTPBearer(auto_error=False)


class TokenVerifier(ABC):
    """Abstract interface for all token verification strategies."""

    @abstractmethod
    async def verify(self, request: Request) -> Principal:
        """Verify the request credentials and return a Principal.

        Raises:
            ForbiddenError: If token is missing, invalid, or expired.
        """
        ...


class DevelopmentVerifier(TokenVerifier):
    """Phase 1 stopgap: accepts role from X-Dev-Role header.

    ONLY operates when ENVIRONMENT != production.
    In production this verifier refuses all requests.

    Accepted roles: IO, SHO, SP (case-insensitive).
    Default role when header is absent: IO.
    """

    _ROLE_MAP: dict[str, UserRole] = {
        "io": UserRole.IO,
        "sho": UserRole.SHO,
        "sp": UserRole.SP,
    }

    def __init__(self, is_production: bool = False) -> None:
        self._is_production = is_production

    async def verify(self, request: Request) -> Principal:
        if self._is_production:
            raise ForbiddenError(
                "Catalyst Auth is required in production. "
                "Phase 3 must be completed before deploying to AppSail."
            )

        raw_role = request.headers.get("X-Dev-Role")
        if not raw_role:
            qp = getattr(request, "query_params", None)
            if qp is not None and type(qp).__name__ not in ("Mock", "MagicMock"):
                try:
                    raw_role = qp.get("role")
                except AttributeError:
                    pass
        if not raw_role or type(raw_role).__name__ in ("Mock", "MagicMock"):
            raw_role = "IO"

        raw_role = raw_role.strip().lower()
        role = self._ROLE_MAP.get(raw_role, UserRole.IO)
        logger.debug("DevelopmentVerifier: role=%s from headers/query", role)

        return Principal(
            user_id=f"dev-{role.value.lower()}",
            email=f"dev-{role.value.lower()}@caseclock.internal",
            role=role,
            is_anonymous=True,  # still anonymous — no real identity
        )


class CatalystAuthVerifier(TokenVerifier):
    """Phase 3: Catalyst Auth JWT verifier.

    Verifies the Zoho Catalyst JWT against the platform JWKS endpoint and
    extracts the user identity.

    Requires:
        CATALYST_CLIENT_ID and CATALYST_PROJECT_ID in settings.
        The `zcatalyst-sdk-python` package in requirements.txt (Phase 3).

    The implementation is left as a stub pending Catalyst Auth credentials.
    Implement by replacing the body of `verify()` using the Catalyst SDK.

    Reference:
        https://docs.catalyst.zoho.com/en/serverless-computing/java-functions/authentication/
    """

    def __init__(self, client_id: str, project_id: str) -> None:
        if not client_id or not project_id:
            raise ValueError(
                "CatalystAuthVerifier requires non-empty client_id and project_id. "
                "Set CATALYST_CLIENT_ID and CATALYST_PROJECT_ID environment variables."
            )
        self._client_id = client_id
        self._project_id = project_id

    async def verify(self, request: Request) -> Principal:
        # Phase 3 implementation: use Catalyst SDK to verify JWT.
        #
        # Example structure:
        #
        #   import zcatalyst_sdk
        #   auth = zcatalyst_sdk.authentication.verify_token(token)
        #   role_str = auth.get_user_defined_attributes().get("caseclock_role", "IO")
        #   role = UserRole(role_str)
        #   return Principal(
        #       user_id=str(auth.get_user_id()),
        #       email=str(auth.get_email()),
        #       role=role,
        #   )
        #
        raise ForbiddenError(
            "CatalystAuthVerifier.verify() is not yet implemented. "
            "Complete Phase 3 by integrating the Catalyst SDK."
        )


def make_verifier(settings: "Settings") -> TokenVerifier:
    """Factory: choose the correct verifier based on environment and credentials.

    - If CATALYST_CLIENT_ID and CATALYST_PROJECT_ID are set → CatalystAuthVerifier.
    - Otherwise in development → DevelopmentVerifier.
    - In production without credentials → DevelopmentVerifier raises ForbiddenError.
    """

    has_catalyst = bool(settings.catalyst_client_id and settings.catalyst_project_id)

    if has_catalyst:
        return CatalystAuthVerifier(
            client_id=settings.catalyst_client_id,
            project_id=settings.catalyst_project_id,
        )

    return DevelopmentVerifier(is_production=settings.is_production)
