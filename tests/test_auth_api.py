
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def active_user():
    return SimpleNamespace(
        id=uuid4(),
        email="test@example.com",
        role="customer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def test_get_me_with_valid_token(client, mock_db, active_user):
    mock_db.get.return_value = active_user

    token = create_access_token(active_user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == active_user.email
    assert response.json()["id"] == str(active_user.id)


def test_get_me_without_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_get_me_with_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_get_me_with_expired_token(client, active_user):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(active_user.id),
        "iat": now - timedelta(minutes=60),
        "exp": now - timedelta(minutes=30),
    }

    expired_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_get_me_with_unknown_user(client, mock_db, active_user):
    mock_db.get.return_value = None

    token = create_access_token(active_user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_get_me_with_inactive_user(client, mock_db, active_user):
    active_user.is_active = False
    mock_db.get.return_value = active_user

    token = create_access_token(active_user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
