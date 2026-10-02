"""로그인 사용자의 Chat JSON API HTTP layer다."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.chat.application import (
    get_chat_exchange,
    list_chat_exchange_history,
    process_chat,
)
from app.chat.errors import ChatError
from app.chat.http import chat_error_to_app_error, normalize_user_agent
from app.chat.schemas import (
    ChatExchangeResponse,
    ChatRequest,
)
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.core.schemas import ErrorResponse

router = APIRouter()


@router.post(
    "/api/chat-exchanges",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatExchangeResponse,
    responses={
        201: {
            "description": "저장된 대화 resource를 생성했습니다.",
            "headers": {
                "Location": {
                    "description": "생성된 대화 URL",
                    "schema": {"type": "string"},
                }
            },
        },
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {
            "model": ErrorResponse,
            "headers": {
                "Retry-After": {
                    "description": "다시 전송하기 전 대기할 초",
                    "schema": {"type": "integer"},
                }
            },
        },
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def post_chat(
    payload: ChatRequest,
    request: Request,
    response: Response,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> ChatExchangeResponse:
    """질문을 처리하고 저장이 완료된 answer를 반환한다."""

    try:
        result = await process_chat(
            user_id=user_id,
            message=payload.message,
            request_id=get_request_id(request),
            user_agent=normalize_user_agent(request.headers.get("user-agent")),
            db=db,
            app_settings=app_settings,
        )
    except ChatError as error:
        raise chat_error_to_app_error(error) from error

    response.headers["Location"] = f"/api/chat-exchanges/{result.chat_exchange_id}"
    response.headers["Cache-Control"] = "no-store"
    return ChatExchangeResponse(
        chat_exchange_id=result.chat_exchange_id,
        question=payload.message,
        answer=result.answer,
        status="success",
        created_at=result.created_at,
    )


@router.get(
    "/api/chat-exchanges",
    response_model=list[ChatExchangeResponse],
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_chat_exchanges(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatExchangeResponse]:
    """로그인 사용자의 전체 대화 기록을 최신순으로 반환한다."""

    try:
        return [
            ChatExchangeResponse.model_validate(item)
            for item in list_chat_exchange_history(user_id=user_id, db=db)
        ]
    except ChatError as error:
        raise chat_error_to_app_error(error) from error


@router.get(
    "/api/chat-exchanges/{chat_exchange_id}",
    response_model=ChatExchangeResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_chat_exchange_by_id(
    chat_exchange_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatExchangeResponse:
    """로그인 사용자가 소유한 단일 대화 기록을 반환한다."""

    try:
        exchange = get_chat_exchange(
            user_id=user_id,
            chat_exchange_id=chat_exchange_id,
            db=db,
        )
    except ChatError as error:
        raise chat_error_to_app_error(error) from error
    if exchange is None:
        raise AppError(status_code=404, code="conversation_not_found")
    return ChatExchangeResponse.model_validate(exchange)
