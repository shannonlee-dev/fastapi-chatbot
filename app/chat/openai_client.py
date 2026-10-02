"""OpenAI SDK 호출을 Chat domain의 answer 생성 계약으로 감싼다."""

from __future__ import annotations

import asyncio
import logging
import math
import random
from collections.abc import Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.chat.context import ChatMessage
from app.chat.errors import (
    ChatConfigurationError,
    ChatGenerationError,
    ChatInvalidResponseError,
    ChatQuotaError,
    ChatRateLimitError,
    ChatTimeoutError,
)
from app.core.config import Settings, settings

logger = logging.getLogger(__name__)
MAX_RETRIES = 2
MAX_RETRY_DELAY_SECONDS = 10.0


def _retry_after_seconds(error: RateLimitError) -> float:
    """Retry-After의 delta seconds·HTTP date를 안전하게 해석한다."""

    value = error.response.headers.get("retry-after")
    if value is None:
        return 0.0
    try:
        delay = float(value)
    except ValueError:
        try:
            instant = parsedate_to_datetime(value)
            delay = (instant - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 0.0
    return max(0.0, delay) if math.isfinite(delay) else 0.0


class OpenAIAnswerGenerator:
    """OpenAI Chat Completions로 text answer를 생성한다."""

    def __init__(
        self, *, client: AsyncOpenAI, model: str, timeout_seconds: float = 30
    ) -> None:
        self._client = client
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(self, *, messages: Sequence[ChatMessage]) -> str:
        """호출과 backoff를 포함한 전체 시간 예산 안에서 답변을 생성한다."""

        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await self._generate(messages=messages)
        except TimeoutError as error:
            raise ChatTimeoutError() from error

    async def _generate(self, *, messages: Sequence[ChatMessage]) -> str:
        """429만 제한적으로 재시도하고 비어 있지 않은 answer를 반환한다."""

        for attempt in range(MAX_RETRIES + 1):
            try:
                completion = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                )
                break
            except RateLimitError as error:
                if error.code == "insufficient_quota":
                    raise ChatQuotaError() from error
                delay = max(2.0**attempt, _retry_after_seconds(error))
                if attempt == MAX_RETRIES or delay > MAX_RETRY_DELAY_SECONDS:
                    raise ChatRateLimitError(retry_after=math.ceil(delay)) from error
                delay += random.uniform(0.0, 0.25)
                logger.warning(
                    "ai_retry_scheduled attempt=%s delay_seconds=%.3f",
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)
            except APITimeoutError as error:
                raise ChatTimeoutError() from error
            except APIError as error:
                raise ChatGenerationError() from error
        else:
            raise ChatRateLimitError()

        if not completion.choices:
            raise ChatInvalidResponseError()

        answer = completion.choices[0].message.content
        if not isinstance(answer, str) or not answer.strip():
            raise ChatInvalidResponseError()
        return answer


def create_openai_client(*, app_settings: Settings | None = None) -> AsyncOpenAI:
    """공용 settings로 timeout과 retry 정책이 반영된 client를 생성한다."""

    configured = app_settings or settings
    api_key = configured.openai_api_key
    if api_key is None:
        raise ChatConfigurationError()

    return AsyncOpenAI(
        api_key=api_key.get_secret_value(),
        timeout=configured.openai_timeout_seconds,
        max_retries=0,
    )
