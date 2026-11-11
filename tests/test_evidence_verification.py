
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.verification import EvidenceVerification
from app.services import evidence_verification_service as verifier


def make_groq_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.call_args = None

    def create(self, **kwargs):
        self.call_args = kwargs
        return make_groq_response(self.content)


class FakeGroqClient:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(
            completions=self.completions
        )


def test_supported_verification_schema():
    result = EvidenceVerification(
        is_supported=True,
        supporting_source_ids=["S1"],
    )

    assert result.is_supported is True
    assert result.supporting_source_ids == ["S1"]


def test_unsupported_verification_schema():
    result = EvidenceVerification(
        is_supported=False,
        supporting_source_ids=[],
    )

    assert result.is_supported is False
    assert result.supporting_source_ids == []


def test_supported_answer_requires_sources():
    with pytest.raises(ValidationError):
        EvidenceVerification(
            is_supported=True,
            supporting_source_ids=[],
        )


def test_unsupported_answer_cannot_have_sources():
    with pytest.raises(ValidationError):
        EvidenceVerification(
            is_supported=False,
            supporting_source_ids=["S1"],
        )


def test_duplicate_source_ids_are_rejected():
    with pytest.raises(ValidationError):
        EvidenceVerification(
            is_supported=True,
            supporting_source_ids=["S1", "S1"],
        )


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        EvidenceVerification.model_validate(
            {
                "is_supported": True,
                "supporting_source_ids": ["S1"],
                "extra_field": "unexpected",
            }
        )


def test_valid_evidence_verification(monkeypatch):
    client = FakeGroqClient(
        json.dumps(
            {
                "is_supported": True,
                "supporting_source_ids": ["S1"],
            }
        )
    )

    monkeypatch.setattr(
        verifier,
        "get_groq_client",
        lambda: client,
    )

    sources = [
        {
            "source_id": "S1",
            "content": "Delivery takes 2 to 4 business days.",
        }
    ]

    result = verifier.verify_answer_evidence(
        question="What is the delivery time?",
        answer="Delivery takes 2 to 4 business days.",
        available_sources=sources,
    )

    assert result.is_supported is True
    assert result.supporting_source_ids == ["S1"]

    assert client.completions.call_args is not None


def test_unsupported_evidence_verification(monkeypatch):
    client = FakeGroqClient(
        json.dumps(
            {
                "is_supported": False,
                "supporting_source_ids": [],
            }
        )
    )

    monkeypatch.setattr(
        verifier,
        "get_groq_client",
        lambda: client,
    )

    result = verifier.verify_answer_evidence(
        question="Does the store deliver internationally?",
        answer="The store delivers internationally.",
        available_sources=[
            {
                "source_id": "S1",
                "content": "The policy only describes domestic delivery.",
            }
        ],
    )

    assert result.is_supported is False
    assert result.supporting_source_ids == []


def test_unknown_source_id_is_rejected(monkeypatch):
    client = FakeGroqClient(
        json.dumps(
            {
                "is_supported": True,
                "supporting_source_ids": ["S99"],
            }
        )
    )

    monkeypatch.setattr(
        verifier,
        "get_groq_client",
        lambda: client,
    )

    with pytest.raises(verifier.EvidenceVerificationError):
        verifier.verify_answer_evidence(
            question="What is the delivery time?",
            answer="Delivery takes 2 to 4 days.",
            available_sources=[
                {
                    "source_id": "S1",
                    "content": "Delivery takes 2 to 4 days.",
                }
            ],
        )


def test_malformed_json_is_rejected(monkeypatch):
    client = FakeGroqClient("This is not valid JSON.")

    monkeypatch.setattr(
        verifier,
        "get_groq_client",
        lambda: client,
    )

    with pytest.raises(verifier.EvidenceVerificationError):
        verifier.verify_answer_evidence(
            question="What is the delivery time?",
            answer="Delivery takes 2 to 4 days.",
            available_sources=[
                {
                    "source_id": "S1",
                    "content": "Delivery takes 2 to 4 days.",
                }
            ],
        )


def test_empty_response_is_rejected(monkeypatch):
    client = FakeGroqClient("")

    monkeypatch.setattr(
        verifier,
        "get_groq_client",
        lambda: client,
    )

    with pytest.raises(verifier.EvidenceVerificationError):
        verifier.verify_answer_evidence(
            question="What is the delivery time?",
            answer="Delivery takes 2 to 4 days.",
            available_sources=[
                {
                    "source_id": "S1",
                    "content": "Delivery takes 2 to 4 days.",
                }
            ],
        )
