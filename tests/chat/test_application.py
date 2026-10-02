"""Chat 공개 진입점의 client 수명·설정·요청 metadata 계약을 검증한다."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Self

import pytest
from sqlalchemy.orm import Session

import app.chat.application as application_module
from app.chat.context import SYSTEM_PROMPT, ChatMessage
from app.chat.errors import ChatConfigurationError
from app.chat.models import ChatExchange


class FakeAsyncOpenAIClient:
    """Production wrapper의 client context manager 경계만 대체한다."""

    def __init__(self) -> None:
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True


def test_application_logs_safely_before_client_configuration_failure(
    db: Session,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_client_creation(**kwargs: object) -> object:
        raise ChatConfigurationError()

    monkeypatch.setattr(
        application_module, "create_openai_client", fail_client_creation
    )

    with (
        caplog.at_level("INFO", logger="app.chat.application"),
        pytest.raises(ChatConfigurationError),
    ):
        asyncio.run(
            application_module.process_chat(
                user_id=1,
                message="SELECT stack api-key Cookie internal error_message",
                request_id="wrapper-config-id",
                user_agent="Cookie secret",
                db=db,
            )
        )

    assert [record.getMessage() for record in caplog.records] == [
        "request_received request_id=wrapper-config-id"
    ]


def test_application_does_not_revalidate_message_before_persistence(
    db: Session,
    user_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncOpenAIClient()
    received: dict[str, object] = {}
    current_time = 10.0

    def fake_perf_counter() -> float:
        return current_time

    def create_client(**kwargs: object) -> FakeAsyncOpenAIClient:
        nonlocal current_time
        current_time = 10.2
        return client

    class FakeProductionGenerator:
        def __init__(
            self, *, client: object, model: str, timeout_seconds: float
        ) -> None:
            received.update({"client": client, "model": model})

        async def generate(self, *, messages: Sequence[ChatMessage]) -> str:
            nonlocal current_time
            current_time = 10.5
            received["messages"] = list(messages)
            return "production wrapper answer"

    monkeypatch.setattr(application_module.time, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(application_module, "create_openai_client", create_client)
    monkeypatch.setattr(application_module.settings, "openai_model", "configured-model")
    monkeypatch.setattr(
        application_module, "OpenAIAnswerGenerator", FakeProductionGenerator
    )

    result = asyncio.run(
        application_module.process_chat(
            user_id=user_id,
            message="  wrapper question  ",
            request_id="wrapper-success-request",
            user_agent="wrapper-agent",
            db=db,
        )
    )
    saved = db.get(ChatExchange, result.chat_exchange_id)

    assert client.closed is True
    assert received["client"] is client
    assert received["model"] == "configured-model"
    assert received["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "  wrapper question  "},
    ]
    assert saved is not None
    assert (
        saved.question,
        saved.answer,
        saved.request_id,
        saved.user_agent,
        saved.response_time_ms,
    ) == (
        "  wrapper question  ",
        "production wrapper answer",
        "wrapper-success-request",
        "wrapper-agent",
        500,
    )
