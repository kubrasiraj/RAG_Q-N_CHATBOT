
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.verification import EvidenceVerification
from app.services import qa_service
from app.services.citation_service import InvalidCitationError
from app.services.evidence_verification_service import (
    EvidenceVerificationError,
)
from app.services.qa_service import (
    InvalidLLMResponseError,
    ask_question,
)


USER_ID = uuid4()
OTHER_USER_ID = uuid4()
DOCUMENT_ID = uuid4()


def make_search_results():
    document = SimpleNamespace(
        id=DOCUMENT_ID,
        original_filename="delivery_policy.txt",
    )

    chunk = SimpleNamespace(
        content="Delivery takes 2 to 4 business days.",
        document=document,
        page_number=1,
        chunk_index=0,
    )

    return [
        {
            "chunk": chunk,
            "similarity": 0.91,
        }
    ]


def make_sources():
    return [
        {
            "source_id": "S1",
            "document_id": DOCUMENT_ID,
            "filename": "delivery_policy.txt",
            "page_number": 1,
            "chunk_index": 0,
            "similarity": 0.91,
            "excerpt": "Delivery takes 2 to 4 business days.",
        }
    ]


def make_supported_llm_response():
    return json.dumps(
        {
            "answer": "Delivery takes 2 to 4 business days.",
            "citation_ids": ["S1"],
            "insufficient_context": False,
        }
    )


def setup_qa_pipeline(monkeypatch):
    monkeypatch.setattr(
        qa_service,
        "embed_query",
        lambda question: [0.1] * 384,
    )

    monkeypatch.setattr(
        qa_service,
        "search_similar_chunks",
        lambda **kwargs: make_search_results(),
    )

    monkeypatch.setattr(
        qa_service,
        "build_retrieval_context",
        lambda results: (
            "Delivery takes 2 to 4 business days.",
            make_sources(),
        ),
    )

    monkeypatch.setattr(
        qa_service,
        "generate_llm_response",
        lambda **kwargs: make_supported_llm_response(),
    )


def test_supported_answer_returns_verified_sources(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        lambda **kwargs: EvidenceVerification(
            is_supported=True,
            supporting_source_ids=["S1"],
        ),
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is False
    assert result.answer == "Delivery takes 2 to 4 business days."
    assert len(result.sources) == 1
    assert result.sources[0].source_id == "S1"


def test_unsupported_answer_returns_no_sources(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        lambda **kwargs: EvidenceVerification(
            is_supported=False,
            supporting_source_ids=[],
        ),
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is True
    assert result.sources == []
    assert "could not verify" in result.answer.lower()


def test_verifier_error_returns_safe_abstention(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    def raise_verification_error(**kwargs):
        raise EvidenceVerificationError(
            "Invalid verifier response."
        )

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        raise_verification_error,
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is True
    assert result.sources == []


def test_invalid_citation_raises_error(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    def raise_invalid_citation(**kwargs):
        raise InvalidCitationError("Unknown citation.")

    monkeypatch.setattr(
        qa_service,
        "validate_citations",
        raise_invalid_citation,
    )

    with pytest.raises(InvalidLLMResponseError):
        ask_question(
            db=None,
            user_id=USER_ID,
            question="What is the delivery time?",
        )


def test_llm_insufficient_context_skips_verification(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    monkeypatch.setattr(
        qa_service,
        "generate_llm_response",
        lambda **kwargs: json.dumps(
            {
                "answer": "The documents do not specify this.",
                "citation_ids": [],
                "insufficient_context": True,
            }
        ),
    )

    def verifier_should_not_run(**kwargs):
        pytest.fail(
            "Verifier should not run for insufficient context."
        )

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        verifier_should_not_run,
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is True
    assert result.sources == []


def test_no_search_results_skips_llm(monkeypatch):
    monkeypatch.setattr(
        qa_service,
        "embed_query",
        lambda question: [0.1] * 384,
    )

    monkeypatch.setattr(
        qa_service,
        "search_similar_chunks",
        lambda **kwargs: [],
    )

    def llm_should_not_run(**kwargs):
        pytest.fail(
            "LLM should not run without search results."
        )

    monkeypatch.setattr(
        qa_service,
        "generate_llm_response",
        llm_should_not_run,
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is True
    assert result.sources == []


def test_invalid_llm_json_raises_error(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    monkeypatch.setattr(
        qa_service,
        "generate_llm_response",
        lambda **kwargs: "This is not valid JSON",
    )

    with pytest.raises(InvalidLLMResponseError):
        ask_question(
            db=None,
            user_id=USER_ID,
            question="What is the delivery time?",
        )



def test_only_verified_sources_are_returned(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    second_chunk = SimpleNamespace(
        content="Additional delivery information.",
        document=SimpleNamespace(
            id=DOCUMENT_ID,
            original_filename="delivery_policy.txt",
        ),
        page_number=2,
        chunk_index=1,
    )

    second_result = {
        "chunk": second_chunk,
        "similarity": 0.85,
    }

    search_results = make_search_results() + [second_result]

    monkeypatch.setattr(
        qa_service,
        "search_similar_chunks",
        lambda **kwargs: search_results,
    )

    second_source = {
        "source_id": "S2",
        "document_id": DOCUMENT_ID,
        "filename": "delivery_policy.txt",
        "page_number": 2,
        "chunk_index": 1,
        "similarity": 0.85,
        "excerpt": "Additional delivery information.",
    }

    monkeypatch.setattr(
        qa_service,
        "build_retrieval_context",
        lambda results: (
            "Delivery takes 2 to 4 business days. "
            "Additional delivery information.",
            make_sources() + [second_source],
        ),
    )

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        lambda **kwargs: EvidenceVerification(
            is_supported=True,
            supporting_source_ids=["S1"],
        ),
    )

    result = ask_question(
        db=None,
        user_id=USER_ID,
        question="What is the delivery time?",
    )

    assert result.insufficient_context is False
    assert len(result.sources) == 1
    assert result.sources[0].source_id == "S1"
    assert all(
        source.source_id != "S2"
        for source in result.sources
    )



def test_search_receives_authenticated_user_and_top_k(monkeypatch):
    setup_qa_pipeline(monkeypatch)

    captured = {}

    def mock_search(**kwargs):
        captured.update(kwargs)
        return make_search_results()

    monkeypatch.setattr(
        qa_service,
        "search_similar_chunks",
        mock_search,
    )

    monkeypatch.setattr(
        qa_service,
        "verify_answer_evidence",
        lambda **kwargs: EvidenceVerification(
            is_supported=True,
            supporting_source_ids=["S1"],
        ),
    )

    ask_question(
        db=None,
        user_id=OTHER_USER_ID,
        question="What is the delivery time?",
        top_k=3,
    )

    assert captured["user_id"] == OTHER_USER_ID
    assert captured["top_k"] == 3
    assert captured["query_embedding"] == [0.1] * 384


@pytest.mark.parametrize(
    "invalid_response",
    [
        json.dumps(
            {
                "answer": "",
                "citation_ids": ["S1"],
                "insufficient_context": False,
            }
        ),
        json.dumps(
            {
                "answer": "Delivery takes 2 to 4 days.",
                "citation_ids": [],
                "insufficient_context": False,
            }
        ),
        json.dumps(
            {
                "answer": "The answer is unavailable.",
                "citation_ids": ["S1"],
                "insufficient_context": True,
            }
        ),
    ],
)
def test_invalid_llm_answer_schema_is_rejected(
    monkeypatch,
    invalid_response,
):
    setup_qa_pipeline(monkeypatch)

    monkeypatch.setattr(
        qa_service,
        "generate_llm_response",
        lambda **kwargs: invalid_response,
    )

    with pytest.raises(InvalidLLMResponseError):
        ask_question(
            db=None,
            user_id=USER_ID,
            question="What is the delivery time?",
        )


@pytest.mark.parametrize(
    "question",
    [
        "ab",
        " ",
        "x" * 2001,
    ],
)
def test_invalid_questions_are_rejected(question):
    with pytest.raises(ValueError):
        ask_question(
            db=None,
            user_id=USER_ID,
            question=question,
        )


@pytest.mark.parametrize("top_k", [0, 11])
def test_invalid_top_k_is_rejected(top_k):
    with pytest.raises(ValueError):
        ask_question(
            db=None,
            user_id=USER_ID,
            question="What is the delivery time?",
            top_k=top_k,
        )
