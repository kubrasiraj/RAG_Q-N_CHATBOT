
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
from app.services.document_service import DocumentNotFoundError


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def active_user():
    return SimpleNamespace(
        id=uuid4(),
        email="test@example.com",
        role="customer",
        is_active=True,
    )


@pytest.fixture
def client(mock_db, active_user):
    def override_get_db():
        yield mock_db

    def override_current_user():
        return active_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_document(active_user):
    now = datetime.now(timezone.utc)

    return SimpleNamespace(
        id=uuid4(),
        user_id=active_user.id,
        original_filename="sample.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        status="pending",
        page_count=None,
        created_at=now,
        updated_at=now,
        processed_at=None,
    )


def test_upload_document_success(
    client,
    active_user,
    monkeypatch,
    sample_document,
):
    async def mock_validate(file):
        return b"sample pdf content"

    def mock_create_document(db, user, original_filename, content):
        assert user.id == active_user.id
        assert original_filename == "sample.pdf"
        assert content == b"sample pdf content"
        return sample_document

    monkeypatch.setattr(
        document_api,
        "validate_document_upload",
        mock_validate,
    )
    monkeypatch.setattr(
        document_api,
        "create_document",
        mock_create_document,
    )

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", b"sample pdf content", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "sample.pdf"
    assert response.json()["status"] == "pending"


def test_upload_document_validation_error(client, monkeypatch):
    async def mock_validate(file):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format.",
        )

    monkeypatch.setattr(
        document_api,
        "validate_document_upload",
        mock_validate,
    )

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.exe", b"invalid content")},
    )

    assert response.status_code == 415


def test_list_documents_success(
    client,
    active_user,
    mock_db,
    monkeypatch,
    sample_document,
):
    def mock_get_user_documents(db, user_id, skip, limit):
        assert user_id == active_user.id
        return [sample_document], 1

    monkeypatch.setattr(
        document_api,
        "get_user_documents",
        mock_get_user_documents,
    )

    response = client.get("/api/v1/documents/")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1


def test_retrieve_document_success(
    client,
    active_user,
    monkeypatch,
    sample_document,
):
    def mock_get_document(db, user_id, document_id):
        assert user_id == active_user.id
        assert document_id == sample_document.id
        return sample_document

    monkeypatch.setattr(
        document_api,
        "get_document_by_id",
        mock_get_document,
    )

    response = client.get(
        f"/api/v1/documents/{sample_document.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(sample_document.id)


def test_retrieve_document_not_found(client, monkeypatch):
    def mock_get_document(db, user_id, document_id):
        raise DocumentNotFoundError("Document not found.")

    monkeypatch.setattr(
        document_api,
        "get_document_by_id",
        mock_get_document,
    )

    response = client.get(
        f"/api/v1/documents/{uuid4()}"
    )

    assert response.status_code == 404


def test_delete_document_success(
    client,
    active_user,
    monkeypatch,
    sample_document,
):
    def mock_delete_document(db, user_id, document_id):
        assert user_id == active_user.id
        assert document_id == sample_document.id

    monkeypatch.setattr(
        document_api,
        "delete_user_document",
        mock_delete_document,
    )

    response = client.delete(
        f"/api/v1/documents/{sample_document.id}"
    )

    assert response.status_code == 204
    assert response.content == b""


def test_delete_document_not_found(client, monkeypatch):
    def mock_delete_document(db, user_id, document_id):
        raise DocumentNotFoundError("Document not found.")

    monkeypatch.setattr(
        document_api,
        "delete_user_document",
        mock_delete_document,
    )

    response = client.delete(
        f"/api/v1/documents/{uuid4()}"
    )

    assert response.status_code == 404
