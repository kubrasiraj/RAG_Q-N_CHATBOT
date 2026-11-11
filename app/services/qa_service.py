import logging
import time
from typing import Any, Callable, TypeVar
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas.qa import (
    LLMAnswer,
    QAResponse,
    QASource,
)
from app.services.citation_service import (
    InvalidCitationError,
    validate_citations,
)
from app.services.context_builder import build_retrieval_context
from app.services.embedding_service import embed_query
from app.services.evidence_verification_service import (
    EvidenceVerificationError,
    verify_answer_evidence,
)
from app.services.llm_service import generate_llm_response
from app.services.vector_search import search_similar_chunks


logger = logging.getLogger(__name__)

T = TypeVar("T")


class QAServiceError(Exception):
    """Base exception for QA service failures."""


class InvalidLLMResponseError(QAServiceError):
    """Raised when the LLM returns invalid or unsafe output."""


def _run_stage(
    stage_name: str,
    operation: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute one QA pipeline stage and record its duration.

    Logs execution time without exposing user data or document content.
    """

    start_time = time.perf_counter()

    try:
        result = operation(*args, **kwargs)

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.warning(
            "QA pipeline stage failed. "
            "stage=%s error_type=%s duration_ms=%.2f",
            stage_name,
            type(exc).__name__,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "QA pipeline stage completed. "
        "stage=%s duration_ms=%.2f",
        stage_name,
        duration_ms,
    )

    return result


def ask_question(
    db: Session,
    user_id: UUID,
    question: str,
    top_k: int = 5,
) -> QAResponse:
    """
    Answer a question using the authenticated user's documents.

    Pipeline:
    query embedding -> vector retrieval -> context construction
    -> LLM generation -> response validation
    -> citation validation -> independent evidence verification.

    Records individual stage durations and total request duration.
    """

    request_start = time.perf_counter()
    outcome = "error"

    try:
        response = _ask_question_pipeline(
            db=db,
            user_id=user_id,
            question=question,
            top_k=top_k,
        )

        outcome = (
            "insufficient_context"
            if response.insufficient_context
            else "success"
        )

        return response

    except Exception as exc:
        logger.warning(
            "QA request failed. error_type=%s",
            type(exc).__name__,
        )
        raise

    finally:
        total_duration_ms = (
            time.perf_counter() - request_start
        ) * 1000

        logger.info(
            "QA request completed. "
            "outcome=%s total_duration_ms=%.2f",
            outcome,
            total_duration_ms,
        )


def _ask_question_pipeline(
    db: Session,
    user_id: UUID,
    question: str,
    top_k: int,
) -> QAResponse:
    """Execute the individual QA pipeline stages."""

    cleaned_question = question.strip()

    if len(cleaned_question) < 3:
        raise ValueError(
            "Question must contain at least 3 characters."
        )

    if len(cleaned_question) > 2000:
        raise ValueError(
            "Question cannot exceed 2000 characters."
        )

    if top_k < 1 or top_k > 10:
        raise ValueError(
            "top_k must be between 1 and 10."
        )

    # 1. Generate question embedding.
    query_embedding = _run_stage(
        "embedding",
        embed_query,
        cleaned_question,
    )

    # 2. Retrieve only this user's completed document chunks.
    search_results = _run_stage(
        "vector_search",
        search_similar_chunks,
        db=db,
        user_id=user_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )

    # 3. Handle empty retrieval.
    if not search_results:
        return QAResponse(
            answer=(
                "I could not find relevant information in your "
                "uploaded documents. Please upload and process "
                "a document containing the information."
            ),
            sources=[],
            insufficient_context=True,
        )

    # 4. Build context and actual source metadata.
    context, available_sources = _run_stage(
        "context_building",
        build_retrieval_context,
        search_results,
    )

    # 5. Generate the LLM response.
    raw_response = _run_stage(
        "llm_generation",
        generate_llm_response,
        question=cleaned_question,
        context=context,
    )

    # 6. Validate the LLM's JSON output.
    try:
        llm_answer = _run_stage(
            "response_validation",
            LLMAnswer.model_validate_json,
            raw_response,
        )

    except ValidationError as exc:
        logger.warning(
            "LLM response validation failed. Errors: %s",
            exc.errors(include_input=False),
        )

        raise InvalidLLMResponseError(
            "The generated answer could not be validated."
        ) from exc

    # 7. Return immediately if the LLM cannot answer.
    if llm_answer.insufficient_context:
        return QAResponse(
            answer=llm_answer.answer,
            sources=[],
            insufficient_context=True,
        )

    # 8. Validate every citation against retrieved source IDs.
    try:
        _run_stage(
            "citation_validation",
            validate_citations,
            citation_ids=llm_answer.citation_ids,
            available_sources=available_sources,
        )

    except InvalidCitationError as exc:
        logger.warning(
            "LLM returned an invalid citation reference."
        )

        raise InvalidLLMResponseError(
            "The generated answer contained invalid source references."
        ) from exc

    # 9. Prepare FULL retrieved chunk content for verification.
    verification_sources = [
        {
            "source_id": source["source_id"],
            "content": result["chunk"].content,
        }
        for source, result in zip(
            available_sources,
            search_results,
            strict=True,
        )
    ]

    # 10. Independently verify factual claims against document evidence.
    try:
        verification = _run_stage(
            "evidence_verification",
            verify_answer_evidence,
            question=cleaned_question,
            answer=llm_answer.answer,
            available_sources=verification_sources,
        )

    except EvidenceVerificationError as exc:
        logger.warning(
            "Evidence verification failed. error_type=%s",
            type(exc).__name__,
        )

        return QAResponse(
            answer=(
                "I could not reliably verify the generated answer "
                "against your uploaded documents. Please try "
                "rephrasing your question."
            ),
            sources=[],
            insufficient_context=True,
        )

    # 11. Fail closed if the answer is not fully supported.
    if not verification.is_supported:
        return QAResponse(
            answer=(
                "I could not verify the complete answer using "
                "the available document evidence."
            ),
            sources=[],
            insufficient_context=True,
        )

    # 12. Only return sources approved by the evidence verifier.
    verified_source_ids = set(
        verification.supporting_source_ids
    )

    verified_sources = [
        source
        for source in available_sources
        if source["source_id"] in verified_source_ids
    ]

    return QAResponse(
        answer=llm_answer.answer,
        sources=[
            QASource.model_validate(source)
            for source in verified_sources
        ],
        insufficient_context=False,
    )