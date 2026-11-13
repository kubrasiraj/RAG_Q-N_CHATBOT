
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Document Q&A RAG API is running"
    )


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_database_health(client, monkeypatch):
    fake_db = MagicMock()

    # Simulate a successful PostgreSQL SELECT 1 query.
    fake_result = MagicMock()
    fake_result.scalar_one.return_value = 1
    fake_db.execute.return_value = fake_result

    def override_get_db():
        return fake_db

    monkeypatch.setitem(
        app.dependency_overrides,
        get_db,
        override_get_db,
    )

    response = client.get("/api/v1/health/db")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["database"] == "connected"

    fake_db.execute.assert_called_once()
