"""Chat use case와 ChatExchange transaction을 처리한다."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Protocol

from app.chat.context import ChatMessage, build_context_messages
from app.chat.errors import (
    ChatGenerationError,
    ChatPersistenceError,
)
from app.chat.models import ChatExchange
from app.chat.repository import ChatExchangeRepository
from app.chat.schemas import ChatExchangeHistoryItem, ChatResult
from app.core.transactions import Transaction

CONTEXT_HISTORY_LIMIT = 5

logger = logging.getLogger(__name__)


class AnswerGenerator(Protocol):
    """Chat Service가 사용하는 answer 생성 계약이다."""

    async def generate(self, *, messages: Sequence[ChatMessage]) -> str:
        """message 목록의 answer를 생성한다."""

        ...


class ChatService:
    """질문 처리, answer 생성, ChatExchange 저장을 하나의 use case로 묶는다."""

    def __init__(
        self,
        *,
        db: Transaction,
        repository: ChatExchangeRepository,
        answer_generator: AnswerGenerator,
    ) -> None:
        self._db = db
        self._repository = repository
        self._answer_generator = answer_generator

    async def execute(
        self,
        *,
        user_id: int,
        message: str,
        request_id: str,
        user_agent: str | None,
        started_at: float,
    ) -> ChatResult:
        """질문을 처리하고 성공·실패 ChatExchange transaction을 완료한다."""

        try:
            exchanges = self._repository.get_recent_success_exchanges(
                user_id=user_id,
                limit=CONTEXT_HISTORY_LIMIT,
            )
            messages = build_context_messages(
                exchanges=exchanges,
                current_question=message,
            )
            self._db.rollback()
        except Exception as error:
            self._db.rollback()
            raise ChatPersistenceError(is_write=False) from error

        try:
            logger.info("ai_call_started request_id=%s", request_id)
            answer = await self._answer_generator.generate(messages=messages)
            logger.info("ai_call_succeeded request_id=%s", request_id)
        except ChatGenerationError as error:
            logger.warning(
                "ai_call_failed request_id=%s code=%s", request_id, error.record_message
            )
            self._save_failed_exchange(
                user_id=user_id,
                question=message,
                error_message=error.record_message,
                request_id=request_id,
                user_agent=user_agent,
                response_time_ms=_elapsed_time_ms(started_at),
                error_code=error.record_message,
            )
            raise
        except Exception:
            logger.warning(
                "ai_call_failed request_id=%s code=internal_error", request_id
            )
            self._save_failed_exchange(
                user_id=user_id,
                question=message,
                error_message="internal_error",
                request_id=request_id,
                user_agent=user_agent,
                response_time_ms=_elapsed_time_ms(started_at),
                error_code="internal_error",
            )
            raise

        try:
            exchange = self._repository.create_success_exchange(
                user_id=user_id,
                question=message,
                answer=answer,
                request_id=request_id,
                user_agent=user_agent,
                response_time_ms=_elapsed_time_ms(started_at),
            )
            result = ChatResult(
                chat_exchange_id=exchange.id,
                answer=answer,
                created_at=exchange.created_at,
            )
            self._db.commit()
            logger.info("db_save_succeeded request_id=%s", request_id)
        except Exception as error:
            self._db.rollback()
            logger.error("db_save_failed request_id=%s", request_id)
            raise ChatPersistenceError() from error

        return result

    def _save_failed_exchange(
        self,
        *,
        user_id: int,
        question: str,
        error_message: str,
        request_id: str,
        user_agent: str | None,
        response_time_ms: int,
        error_code: str,
    ) -> None:
        try:
            self._repository.create_failed_exchange(
                user_id=user_id,
                question=question,
                error_message=error_message,
                request_id=request_id,
                user_agent=user_agent,
                response_time_ms=response_time_ms,
                error_code=error_code,
            )
            self._db.commit()
            logger.info("db_save_succeeded request_id=%s", request_id)
        except Exception as error:
            self._db.rollback()
            logger.error("db_save_failed request_id=%s", request_id)
            raise ChatPersistenceError() from error


class ChatHistoryService:
    """사용자 소유 대화 조회와 안전한 history 변환을 처리한다."""

    def __init__(self, *, db: Transaction, repository: ChatExchangeRepository) -> None:
        self._db = db
        self._repository = repository

    def list_chat_exchange_history(
        self,
        *,
        user_id: int,
    ) -> list[ChatExchangeHistoryItem]:
        """로그인 사용자의 ChatExchange history를 내부 오류 없이 projection한다."""

        try:
            exchanges = self._repository.list_user_exchanges(user_id=user_id)
        except Exception as error:
            self._db.rollback()
            raise ChatPersistenceError(is_write=False) from error

        return [_to_history_item(exchange) for exchange in exchanges]

    def get_chat_exchange(
        self, *, user_id: int, chat_exchange_id: int
    ) -> ChatExchangeHistoryItem | None:
        """사용자 소유의 단일 ChatExchange를 안전한 projection으로 반환한다."""

        try:
            exchange = self._repository.get_user_exchange(
                user_id=user_id,
                chat_exchange_id=chat_exchange_id,
            )
        except Exception as error:
            self._db.rollback()
            raise ChatPersistenceError(is_write=False) from error
        return _to_history_item(exchange) if exchange is not None else None


def _elapsed_time_ms(started_at: float) -> int:
    return max(0, int((time.perf_counter() - started_at) * 1000))


def _to_history_item(exchange: ChatExchange) -> ChatExchangeHistoryItem:
    return ChatExchangeHistoryItem(
        chat_exchange_id=exchange.id,
        question=exchange.question,
        answer=exchange.answer,
        status=exchange.status,
        created_at=exchange.created_at,
    )
