"""backend/app/api/document_routes.py

FastAPI router for Catalyst Evidence Document Intelligence endpoints.

Uses JSON body with base64-encoded file content to avoid requiring
python-multipart at FastAPI route registration time (which caused
AppSail startup crashes when the package was not in the pip cache).
"""

from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.catalyst.document_intelligence import DocumentProviderError

try:
    from backend.app.api.dependencies import get_document_service, get_principal
    from backend.app.auth.principal import Principal
    from backend.app.services.document_service import DocumentService
    from shared.contracts.api import (
        DocumentConfirmRequest,
        DocumentConfirmResponse,
        DocumentScanRequest,
        DocumentScanResponse,
    )
except ImportError:
    from backend.app.api.dependencies import get_document_service, get_principal  # type: ignore
    from backend.app.auth.principal import Principal  # type: ignore
    from backend.app.services.document_service import DocumentService  # type: ignore
    from shared.contracts.api import (  # type: ignore
        DocumentConfirmRequest,
        DocumentConfirmResponse,
        DocumentScanRequest,
        DocumentScanResponse,
    )


def create_document_router() -> APIRouter:
    """Return router for document intelligence endpoints."""
    router = APIRouter(prefix="/cases", tags=["document-intelligence"])

    @router.post(
        "/{case_id}/documents/scan",
        response_model=DocumentScanResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def scan_document(
        case_id: str,
        body: DocumentScanRequest,
        principal: Principal = Depends(get_principal),
        doc_svc: DocumentService = Depends(get_document_service),
    ) -> DocumentScanResponse:
        """Upload an evidence document/FIR via base64 JSON, execute Zia OCR,
        and generate a non-persisted statutory clock preview.

        The file must be base64-encoded in the ``file_base64`` field.
        This avoids the python-multipart dependency at route registration time.
        """
        try:
            try:
                encoded = body.file_base64.strip()
                if not encoded or len(encoded) % 4 or len(encoded) > 28_000_000:
                    raise ValueError("Invalid base64 encoding in file_base64")
                file_bytes = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError(f"Invalid base64 encoding in file_base64: {exc}") from exc

            return doc_svc.scan_document(
                case_id=case_id,
                file_bytes=file_bytes,
                filename=body.filename,
                content_type=body.content_type,
                document_type=body.document_type,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except DocumentProviderError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to scan document: {exc}",
            ) from exc

    @router.post(
        "/{case_id}/documents/{document_id}/confirm",
        response_model=DocumentConfirmResponse,
    )
    def confirm_document(
        case_id: str,
        document_id: str,
        request: DocumentConfirmRequest,
        principal: Principal = Depends(get_principal),
        doc_svc: DocumentService = Depends(get_document_service),
    ) -> DocumentConfirmResponse:
        """Officer confirmation of candidate facts, updating case statutory clock deterministically."""
        try:
            return doc_svc.confirm_document_facts(
                case_id=case_id,
                document_id=document_id,
                request=request,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to confirm document facts: {exc}",
            ) from exc

    return router
