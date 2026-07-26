"""backend/app/api/routes/chat.py

Presentation layer router for AI Chat operations.
Provides FastAPI HTTP transport, dependency injection, and domain exception mapping
for the CaseClock AI subsystem.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.ai.exceptions import (
    AIError,
    AIValidationError,
    PromptError,
    QuickMLAuthError,
    QuickMLConnectionError,
    QuickMLRateLimitError,
    QuickMLResponseError,
    QuickMLTimeoutError,
)
from backend.app.ai.prompt_manager import PromptManager
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.quickml_service import QuickMLService
from backend.app.ai.schemas import ChatRequest, ChatResponse
from backend.app.dependencies.ai import get_quickml_service

router = APIRouter()



@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process AI Chat Query",
    description="Accepts a ChatRequest payload, processes query via QuickMLService, and returns a ChatResponse.",
)
def chat(
    request: ChatRequest,
    service: QuickMLService = Depends(get_quickml_service),
) -> ChatResponse:
    """FastAPI endpoint handling POST /chat requests."""
    try:
        return service.chat(request)
    except QuickMLAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed with QuickML provider.",
        ) from e
    except QuickMLRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="QuickML API rate limit exceeded.",
        ) from e
    except QuickMLTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="QuickML API request timed out.",
        ) from e
    except QuickMLConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to QuickML provider.",
        ) from e
    except QuickMLResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from QuickML provider.",
        ) from e
    except PromptError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load or render prompt template.",
        ) from e
    except AIValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI request payload.",
        ) from e
    except AIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An AI subsystem error occurred.",
        ) from e
