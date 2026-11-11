
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    password = "TestPassword123"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_password_verification():
    password = "TestPassword123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_access_token_creation():
    user_id = uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert isinstance(token, str)
    assert payload["sub"] == str(user_id)
    assert "iat" in payload
    assert "exp" in payload


def test_expired_token_rejected():
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(uuid4()),
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }

    expired_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_invalid_signature_rejected():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }

    invalid_token = jwt.encode(
        payload,
        "wrong-secret-key-that-is-at-least-32-bytes-long",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(invalid_token)


def test_missing_required_claim_rejected():
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(uuid4()),
        "iat": now,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)
