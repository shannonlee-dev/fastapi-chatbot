"""실제 SDK와 HTTP transport를 통해 429 retry 정책을 검증한다."""

import asyncio

import httpx
import pytest
from openai import AsyncOpenAI

from app.chat.errors import ChatGenerationError, ChatTimeoutError
from app.chat.openai_client import OpenAIAnswerGenerator


@pytest.mark.parametrize("failures", [1, 2, 3])
def test_rate_limit_uses_bounded_exponential_backoff(
    monkeypatch: pytest.MonkeyPatch, failures: int
) -> None:
    attempts = 0
    delays: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts <= failures:
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "답변"},
                    }
                ],
            },
        )

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)

    async def run() -> None:
        async with AsyncOpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            generator = OpenAIAnswerGenerator(client=client, model="test")
            if failures == 3:
                with pytest.raises(ChatGenerationError) as caught:
                    await generator.generate(
                        messages=[{"role": "user", "content": "질문"}]
                    )
                assert caught.value.record_message == "openai_rate_limited"
            else:
                assert (
                    await generator.generate(
                        messages=[{"role": "user", "content": "질문"}]
                    )
                    == "답변"
                )

    asyncio.run(run())
    assert attempts == min(failures + 1, 3)
    assert len(delays) == min(failures, 2)
    assert 1 <= delays[0] <= 1.25
    if len(delays) == 2:
        assert 2 <= delays[1] <= 2.25


@pytest.mark.parametrize(
    "code, retry_after",
    [
        ("insufficient_quota", None),
        ("rate_limit_exceeded", "120"),
        ("rate_limit_exceeded", "Wed, 21 Oct 2037 07:28:00 GMT"),
    ],
)
def test_unrecoverable_rate_limit_does_not_retry(
    monkeypatch: pytest.MonkeyPatch, code: str, retry_after: str | None
) -> None:
    attempts = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            429,
            headers={"Retry-After": retry_after} if retry_after else {},
            json={"error": {"code": code}},
        )

    async def run() -> None:
        async with AsyncOpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            with pytest.raises(ChatGenerationError) as caught:
                await OpenAIAnswerGenerator(client=client, model="test").generate(
                    messages=[{"role": "user", "content": "질문"}]
                )
            assert caught.value.record_message == (
                "openai_quota_exceeded"
                if code == "insufficient_quota"
                else "openai_rate_limited"
            )

    asyncio.run(run())
    assert attempts == 1


def test_total_generation_budget_includes_backoff() -> None:
    attempts = 0

    async def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})

    async def run() -> None:
        async with AsyncOpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            with pytest.raises(ChatTimeoutError):
                await OpenAIAnswerGenerator(
                    client=client, model="test", timeout_seconds=0.3
                ).generate(messages=[{"role": "user", "content": "질문"}])

    asyncio.run(run())
    assert attempts == 1


@pytest.mark.parametrize(
    "retry_after, minimum", [("3", 3), ("invalid", 1), ("NaN", 1), ("-5", 1)]
)
def test_retry_after_is_respected_or_ignored_when_invalid(
    monkeypatch: pytest.MonkeyPatch,
    retry_after: str,
    minimum: int,
) -> None:
    attempts = 0
    delays: list[float] = []

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": retry_after},
                json={"error": {"code": "rate_limit_exceeded"}},
            )
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "답변"},
                    }
                ],
            },
        )

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)

    async def run() -> str:
        async with AsyncOpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            return await OpenAIAnswerGenerator(client=client, model="test").generate(
                messages=[{"role": "user", "content": "질문"}]
            )

    assert asyncio.run(run()) == "답변"
    assert attempts == 2
    assert len(delays) == 1
    assert minimum <= delays[0] <= minimum + 0.25
