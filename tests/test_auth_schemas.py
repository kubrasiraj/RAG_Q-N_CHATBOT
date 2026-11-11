
import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
)


def test_valid_user_registration():
    user = UserRegister(
        email="test@example.com",
        password="StrongPassword123",
    )

    assert user.email == "test@example.com"
    assert user.password == "StrongPassword123"


def test_registration_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(
            email="invalid-email",
            password="StrongPassword123",
        )


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        UserRegister(
            email="test@example.com",
            password="short",
        )


def test_registration_rejects_missing_email():
    with pytest.raises(ValidationError):
        UserRegister(
            password="StrongPassword123",
        )


def test_valid_user_login():
    user = UserLogin(
        email="test@example.com",
        password="StrongPassword123",
    )

    assert user.email == "test@example.com"


def test_login_rejects_empty_password():
    with pytest.raises(ValidationError):
        UserLogin(
            email="test@example.com",
            password="",
        )


def test_valid_token_response():
    token = TokenResponse(
        access_token="sample.jwt.token",
    )

    assert token.access_token == "sample.jwt.token"
    assert token.token_type == "bearer"
