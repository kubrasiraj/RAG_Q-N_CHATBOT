
from uuid import uuid4
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from groq import RateLimitError

from app.api.v1 import qa as qa_api
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.main import app


@pytest.fixture
def api_client():
    test_user = SimpleNamespace(
        id=uuid4(),
        is_active=True,
        role="customer",
    )

    app.dependency_overrides[get_current_user] = (
        lambda: test_user
    )
    app.dependency_overrides[get_db] = lambda: None

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def make_rate_limit_error(headers=None):
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
    )

    response = httpx.Response(
        status_code=429,
        headers=headers or {},
        request=request,
    )

    return RateLimitError(
        "Rate limit exceeded.",
        response=response,
        body=None,
    )


def test_rate_limit_returns_503_with_retry_after(
    api_client,
    monkeypatch,
):
    def raise_rate_limit(**kwargs):
        raise make_rate_limit_error(
            {"retry-after": "60"}
        )

    monkeypatch.setattr(
        qa_api,
        "ask_question",
        raise_rate_limit,
    )

    response = api_client.post(
        "/api/v1/qa/ask",
        json={"question": "What is the delivery time?"},
    )
    print("STATUS:", response.status_code)
    print("HEADERS:", dict(response.headers))
    print("BODY:", response.text)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "60"
    assert response.json()["detail"]["code"] == "AI_RATE_LIMITED"


def test_rate_limit_without_retry_after_returns_503(
    api_client,
    monkeypatch,
):
    def raise_rate_limit(**kwargs):
        raise make_rate_limit_error()

    monkeypatch.setattr(
        qa_api,
        "ask_question",
        raise_rate_limit,
    )

    response = api_client.post(
        "/api/v1/qa/ask",
        json={"question": "What is the delivery time?"},
    )

    assert response.status_code == 503
    assert "Retry-After" not in response.headers
    assert response.json()["detail"]["code"] == "AI_RATE_LIMITED"


def test_invalid_retry_after_is_not_forwarded(
    api_client,
    monkeypatch,
):
    def raise_rate_limit(**kwargs):
        raise make_rate_limit_error(
            {"retry-after": "invalid"}
        )

    monkeypatch.setattr(
        qa_api,
        "ask_question",
        raise_rate_limit,
    )

    response = api_client.post(
        "/api/v1/qa/ask",
        json={"question": "What is the delivery time?"},
    )

    assert response.status_code == 503
    assert "Retry-After" not in response.headers
