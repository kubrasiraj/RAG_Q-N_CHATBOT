
"""
Tests for automatic document processing after upload.

Embedding models, document downloads, and extraction are mocked where
appropriate. No real database, Supabase Storage, or Groq API is used.
A small in-memory session stands in for SQLAlchemy so the real
process_document() lifecycle can run end to end.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1 import documents as document_api
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.document import Document
from app.services import document_background, document_processing
from app.services.document_extraction import ExtractedPage, ExtractionResult


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class FakeSession:
    """Minimal stand-in for a SQLAlchemy session holding one Document."""

    def __init__(self, document):
        self.document = document
        self.commit_statuses = []
        self.added = []
        self.executed = []
        self.rollbacks = 0
        self.closed = False

    def get(self, model, identity):
        return self.document if identity == self.document.id else None

    def commit(self):
        self.commit_statuses.append(self.document.status)

    def rollback(self):
        self.rollbacks += 1

    def execute(self, statement):
        self.executed.append(statement)

    def add_all(self, items):
        self.added.extend(items)

    def refresh(self, obj):
        pass

    def close(self):
        self.closed = True


def make_document(user_id, *, status="pending", storage_path="users/test/documents/sample.txt"):
    return Document(
        id=uuid4(),
        user_id=user_id,
        original_filename="notes.txt",
        storage_path=storage_path,
        mime_type="text/plain",
        file_size_bytes=10,
        status=status,
    )


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def sessions(monkeypatch):
    """Patch SessionLocal in the wrapper so every session it opens is recorded."""

    created = []
    state = {"document": None}

    def factory():
        session = FakeSession(state["document"])
        created.append(session)
        return session

    monkeypatch.setattr(document_background, "SessionLocal", factory)

    return SimpleNamespace(created=created, state=state)


def fake_extraction(*args, **kwargs):
    return ExtractionResult(
        file_type="txt",
        pages=[
            ExtractedPage(
                page_number=1,
                content="Employees accrue vacation monthly.",
            )
        ],
        page_count=1,
        ocr_page_numbers=[],
    )


def fake_chunks(pages):
    return [
        SimpleNamespace(
            chunk_index=0,
            content="Employees accrue vacation monthly.",
            page_number=1,
        )
    ]


def fake_download(object_path):
    """Return sample document bytes instead of downloading from Supabase."""
    return b"Employees accrue vacation monthly."


# --------------------------------------------------------------------------- #
# 1. Upload schedules processing
# --------------------------------------------------------------------------- #


@pytest.fixture
def active_user(user_id):
    return SimpleNamespace(
        id=user_id,
        email="test@example.com",
        role="customer",
        is_active=True,
    )


@pytest.fixture
def client(active_user):
    app.dependency_overrides[get_db] = lambda: iter([MagicMock()])
    app.dependency_overrides[get_current_user] = lambda: active_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def upload(
    client,
    monkeypatch,
    *,
    created_document=None,
    create_error=None,
    validation_error=None,
):
    now = datetime.now(timezone.utc)

    document = created_document or SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        original_filename="sample.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        status="pending",
        page_count=None,
        created_at=now,
        updated_at=now,
        processed_at=None,
    )

    scheduled = []

    async def validate(file):
        if validation_error:
            raise validation_error
        return b"content"

    def create(db, user, original_filename, content):
        if create_error:
            raise create_error
        return document

    monkeypatch.setattr(document_api, "validate_document_upload", validate)
    monkeypatch.setattr(document_api, "create_document", create)

    monkeypatch.setattr(
        document_api,
        "run_document_processing",
        lambda document_id, user_id: scheduled.append(
            (document_id, user_id)
        ),
    )

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", b"content", "application/pdf")},
    )

    return response, document, scheduled


def test_upload_schedules_processing_with_plain_ids(
    client,
    active_user,
    monkeypatch,
):
    response, document, scheduled = upload(client, monkeypatch)

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert scheduled == [(document.id, active_user.id)]

    # Only identifiers are handed over, never a session or ORM object.
    assert all(
        not isinstance(arg, (MagicMock, Document))
        for arg in scheduled[0]
    )


def test_upload_does_not_schedule_when_validation_fails(
    client,
    monkeypatch,
):
    response, _, scheduled = upload(
        client,
        monkeypatch,
        validation_error=HTTPException(
            status_code=415,
            detail="Unsupported file format.",
        ),
    )

    assert response.status_code == 415
    assert scheduled == []


def test_upload_does_not_schedule_when_saving_fails(
    client,
    monkeypatch,
):
    response, _, scheduled = upload(
        client,
        monkeypatch,
        create_error=ValueError("Unsupported document extension."),
    )

    assert response.status_code == 400
    assert scheduled == []

    response, _, scheduled = upload(
        client,
        monkeypatch,
        create_error=OSError("storage unavailable"),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to save the uploaded document."
    )
    assert scheduled == []


# --------------------------------------------------------------------------- #
# 2. Background processing uses its own session
# --------------------------------------------------------------------------- #


def test_wrapper_opens_its_own_session_and_always_closes_it(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    calls = []

    monkeypatch.setattr(
        document_background,
        "process_document",
        lambda db, document_id: calls.append((db, document_id)),
    )

    document_background.run_document_processing(document.id, user_id)

    assert len(sessions.created) == 1
    assert calls == [(sessions.created[0], document.id)]
    assert sessions.created[0].closed is True


def test_wrapper_closes_the_session_even_when_processing_raises(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    def boom(db, document_id):
        raise document_processing.DocumentProcessingError(
            "Unable to process document."
        )

    monkeypatch.setattr(
        document_background,
        "process_document",
        boom,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    assert sessions.created[0].closed is True


# --------------------------------------------------------------------------- #
# 3 / 4. Real lifecycle: completed and failed
# --------------------------------------------------------------------------- #


def test_successful_processing_goes_pending_processing_completed(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    # Supabase Storage download mock.
    monkeypatch.setattr(
        document_processing,
        "download_document",
        fake_download,
    )

    monkeypatch.setattr(
        document_processing,
        "extract_document",
        fake_extraction,
    )

    monkeypatch.setattr(
        document_processing,
        "chunk_document_pages",
        fake_chunks,
    )

    monkeypatch.setattr(
        document_processing,
        "embed_texts",
        lambda texts: [[0.1] * 384 for _ in texts],
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    session = sessions.created[0]

    assert session.commit_statuses == ["processing", "completed"]
    assert document.status == "completed"
    assert document.page_count == 1
    assert document.processed_at is not None
    assert len(session.added) == 1
    assert session.closed is True


def test_embedding_failure_marks_the_document_failed_without_leaking_details(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    monkeypatch.setattr(
        document_processing,
        "download_document",
        fake_download,
    )

    monkeypatch.setattr(
        document_processing,
        "extract_document",
        fake_extraction,
    )

    monkeypatch.setattr(
        document_processing,
        "chunk_document_pages",
        fake_chunks,
    )

    def broken_embeddings(texts):
        raise RuntimeError(
            "secret internal model path /srv/models/xyz exploded"
        )

    monkeypatch.setattr(
        document_processing,
        "embed_texts",
        broken_embeddings,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    session = sessions.created[0]

    assert session.commit_statuses == ["processing", "failed"]
    assert document.status == "failed"
    assert document.error_message == "Document processing failed."
    assert "secret" not in document.error_message
    assert session.added == []
    assert session.closed is True


@pytest.mark.parametrize("stage", ["extract", "chunk"])
def test_extraction_and_chunking_failures_mark_the_document_failed(
    stage,
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    monkeypatch.setattr(
        document_processing,
        "download_document",
        fake_download,
    )

    def broken(*args, **kwargs):
        raise ValueError("bad content")

    monkeypatch.setattr(
        document_processing,
        "extract_document",
        broken if stage == "extract" else fake_extraction,
    )

    monkeypatch.setattr(
        document_processing,
        "chunk_document_pages",
        broken if stage == "chunk" else fake_chunks,
    )

    monkeypatch.setattr(
        document_processing,
        "embed_texts",
        lambda texts: [[0.0] * 384 for _ in texts],
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    assert document.status == "failed"
    assert sessions.created[0].commit_statuses == [
        "processing",
        "failed",
    ]


def test_no_usable_text_marks_the_document_failed(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    monkeypatch.setattr(
        document_processing,
        "download_document",
        fake_download,
    )

    monkeypatch.setattr(
        document_processing,
        "extract_document",
        fake_extraction,
    )

    monkeypatch.setattr(
        document_processing,
        "chunk_document_pages",
        lambda pages: [],
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    assert document.status == "failed"


# --------------------------------------------------------------------------- #
# 5. Missing Supabase Storage object
# --------------------------------------------------------------------------- #


def test_missing_source_file_marks_the_document_failed_instead_of_stuck(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(
        user_id,
        storage_path="users/test/documents/missing.txt",
    )

    sessions.state["document"] = document

    def missing_object(object_path):
        raise FileNotFoundError("Object does not exist.")

    monkeypatch.setattr(
        document_processing,
        "download_document",
        missing_object,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    assert document.status == "failed"
    assert document.status != "processing"
    assert sessions.created[0].commit_statuses[-1] == "failed"


# --------------------------------------------------------------------------- #
# Ownership, duplicate protection and the safety net
# --------------------------------------------------------------------------- #


def test_wrapper_never_processes_another_users_document(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(uuid4())
    sessions.state["document"] = document

    process = MagicMock()

    monkeypatch.setattr(
        document_background,
        "process_document",
        process,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    process.assert_not_called()
    assert document.status == "pending"


@pytest.mark.parametrize(
    "status",
    ["processing", "completed", "failed"],
)
def test_wrapper_skips_documents_that_are_not_pending(
    status,
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id, status=status)
    sessions.state["document"] = document

    process = MagicMock()

    monkeypatch.setattr(
        document_background,
        "process_document",
        process,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    process.assert_not_called()
    assert document.status == status


def test_wrapper_ignores_unknown_documents(
    sessions,
    user_id,
    monkeypatch,
):
    sessions.state["document"] = make_document(user_id)

    process = MagicMock()

    monkeypatch.setattr(
        document_background,
        "process_document",
        process,
    )

    document_background.run_document_processing(
        uuid4(),
        user_id,
    )

    process.assert_not_called()


def test_unexpected_error_triggers_the_failed_safety_net_with_a_fresh_session(
    sessions,
    user_id,
    monkeypatch,
):
    document = make_document(user_id)
    sessions.state["document"] = document

    def explode(db, document_id):
        raise ConnectionError("database went away")

    monkeypatch.setattr(
        document_background,
        "process_document",
        explode,
    )

    document_background.run_document_processing(
        document.id,
        user_id,
    )

    assert len(sessions.created) == 2
    assert all(session.closed for session in sessions.created)

    safety_net = sessions.created[1]

    assert len(safety_net.executed) == 1

    sql = str(safety_net.executed[0])

    assert "UPDATE documents" in sql
    assert "status" in sql
    assert safety_net.commit_statuses
