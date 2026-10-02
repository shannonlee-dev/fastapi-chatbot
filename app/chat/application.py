"""Chat의 공개 진입점과 DB·OpenAI 의존성을 조립한다."""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.chat.openai_client import OpenAIAnswerGenerator, create_openai_client
from app.chat.repository import SqlAlchemyChatExchangeRepository
from app.chat.schemas import ChatExchangeHistoryItem, ChatResult
from app.chat.service import ChatHistoryService, ChatService
from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


async def process_chat(
    *,
    user_id: int,
    message: str,
    request_id: str,
    user_agent: str | None = None,
    db: Session,
    app_settings: Settings | None = None,
) -> ChatResult:
    """production 의존성을 조립해 Chat use case를 실행한다."""

    started_at = time.perf_counter()
    logger.info("request_received request_id=%s", request_id)
    repository = SqlAlchemyChatExchangeRepository(db=db)
    configured = app_settings or settings
    async with create_openai_client(app_settings=configured) as client:
        service = ChatService(
            db=db,
            repository=repository,
            answer_generator=OpenAIAnswerGenerator(
                client=client,
                model=configured.openai_model,
                timeout_seconds=configured.openai_timeout_seconds,
            ),
        )
        return await service.execute(
            user_id=user_id,
            message=message,
            request_id=request_id,
            user_agent=user_agent,
            started_at=started_at,
        )


def _create_history_service(db: Session) -> ChatHistoryService:
    return ChatHistoryService(db=db, repository=SqlAlchemyChatExchangeRepository(db=db))


def list_chat_exchange_history(
    *, user_id: int, db: Session
) -> list[ChatExchangeHistoryItem]:
    """사용자 소유의 전체 대화 기록을 안전한 정보로 반환한다."""

    return _create_history_service(db).list_chat_exchange_history(user_id=user_id)


def get_chat_exchange(
    *, user_id: int, chat_exchange_id: int, db: Session
) -> ChatExchangeHistoryItem | None:
    """사용자 소유의 단일 대화 기록을 안전한 정보로 반환한다."""

    return _create_history_service(db).get_chat_exchange(
        user_id=user_id, chat_exchange_id=chat_exchange_id
    )
