
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from groq import APIConnectionError, APIError, RateLimitError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.qa import QARequest, QAResponse
from app.services.qa_service import (
    InvalidLLMResponseError,
    ask_question,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/qa",
    tags=["Question Answering"],
)


@router.post(
    "/ask",
    response_model=QAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about uploaded documents",
)
def ask_document_question(
    request: QARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QAResponse:
    try:
        return ask_question(
            db=db,
            user_id=current_user.id,
            question=request.question,
            top_k=request.top_k,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except InvalidLLMResponseError as exc:
        logger.warning("QA response validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an invalid response. Please try again.",
        ) from exc


    except RateLimitError as exc:
        logger.warning("Groq rate limit reached.")

        response_headers = {}
        retry_after = exc.response.headers.get("retry-after")

        # Forward only a valid numeric Retry-After value.
        if retry_after and retry_after.strip().isdigit():
            response_headers["Retry-After"] = retry_after.strip()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_RATE_LIMITED",
                "message": (
                    "The AI service has reached its rate limit. "
                    "Please try again later."
                ),
            },
            headers=response_headers,
        ) from exc


    except APIConnectionError as exc:
        logger.error("Could not connect to Groq API.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is temporarily unavailable.",
        ) from exc

    except APIError as exc:
        logger.error("Groq API request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not complete your request.",
        ) from exc

    except Exception:
        logger.exception("Unexpected error while answering a document question.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your question.",
        )
