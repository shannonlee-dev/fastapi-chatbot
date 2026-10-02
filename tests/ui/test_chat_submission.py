"""JavaScript 없이 동작하는 Chat form과 PRG를 검증한다."""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser, require_authenticated_user
from app.chat.errors import ChatTimeoutError
from app.chat.service import ChatResult
from app.core.database import get_db
from app.core.request_id import RequestIdMiddleware
from app.ui.router import router


@pytest.fixture
def client(db: Session, user_id: int) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
        user_id=user_id, is_admin=False
    )
    with TestClient(app) as client:
        yield client


def test_chat_form_has_server_action(client: TestClient) -> None:
    response = client.get("/chat")
    assert response.status_code == 200
    assert 'method="post" action="/chat"' in response.text


def test_chat_form_success_redirects_without_reposting(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def generate(**kwargs: object) -> ChatResult:
        assert kwargs["message"] == "질문"
        return ChatResult(
            chat_exchange_id=1, answer="답변", created_at=datetime.now(UTC)
        )

    monkeypatch.setattr("app.ui.router.process_chat", generate, raising=False)
    response = client.post("/chat", data={"message": " 질문 "}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/chat"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("message", ["", " ", "x" * 1001])
def test_invalid_chat_form_renders_safe_error(client: TestClient, message: str) -> None:
    response = client.post("/chat", data={"message": message})
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "질문" in response.text
    assert 'id="chat-form-error"' in response.text


def test_chat_form_timeout_renders_html_and_keeps_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def timeout(**kwargs: object) -> ChatResult:
        raise ChatTimeoutError()

    monkeypatch.setattr("app.ui.router.process_chat", timeout, raising=False)
    response = client.post("/chat", data={"message": "<script>test</script>"})
    assert response.status_code == 504
    assert "시간이 초과" in response.text
    assert "<script>test</script>" not in response.text
    assert "&lt;script&gt;test&lt;/script&gt;" in response.text
    assert response.headers["cache-control"] == "no-store"
