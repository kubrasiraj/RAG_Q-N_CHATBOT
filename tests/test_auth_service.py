
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.services import auth_service


@pytest.fixture
def db():
    return MagicMock(spec=Session)


def test_get_user_by_email(db):
    expected_user = SimpleNamespace(email="test@example.com")
    db.scalar.return_value = expected_user

    result = auth_service.get_user_by_email(
        db,
        "TEST@EXAMPLE.COM",
    )

    assert result is expected_user
    db.scalar.assert_called_once()


def test_register_user_success(db, monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: None,
    )

    user = auth_service.register_user(
        db,
        " TEST@EXAMPLE.COM ",
        "StrongPassword123",
    )

    assert user.email == "test@example.com"
    assert user.hashed_password != "StrongPassword123"
    assert user.role == "customer"
    assert user.is_active is True

    db.add.assert_called_once_with(user)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(user)


def test_register_duplicate_email(db, monkeypatch):
    existing_user = SimpleNamespace(
        email="test@example.com"
    )

    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: existing_user,
    )

    with pytest.raises(
        auth_service.EmailAlreadyRegisteredError
    ):
        auth_service.register_user(
            db,
            "test@example.com",
            "StrongPassword123",
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_authenticate_user_success(db, monkeypatch):
    password = "StrongPassword123"

    user = SimpleNamespace(
        email="test@example.com",
        hashed_password=hash_password(password),
        is_active=True,
    )

    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: user,
    )

    result = auth_service.authenticate_user(
        db,
        "test@example.com",
        password,
    )

    assert result is user


def test_authenticate_user_wrong_password(db, monkeypatch):
    user = SimpleNamespace(
        email="test@example.com",
        hashed_password=hash_password("CorrectPassword123"),
        is_active=True,
    )

    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: user,
    )

    result = auth_service.authenticate_user(
        db,
        "test@example.com",
        "WrongPassword123",
    )

    assert result is None


def test_authenticate_user_not_found(db, monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: None,
    )

    result = auth_service.authenticate_user(
        db,
        "unknown@example.com",
        "StrongPassword123",
    )

    assert result is None


def test_authenticate_inactive_user(db, monkeypatch):
    user = SimpleNamespace(
        email="test@example.com",
        hashed_password=hash_password("StrongPassword123"),
        is_active=False,
    )

    monkeypatch.setattr(
        auth_service,
        "get_user_by_email",
        lambda db, email: user,
    )

    result = auth_service.authenticate_user(
        db,
        "test@example.com",
        "StrongPassword123",
    )

    assert result is None
