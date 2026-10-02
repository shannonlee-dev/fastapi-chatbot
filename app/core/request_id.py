"""HTTP request 추적 ID를 생성하고 전달한다."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import current_request_id

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_STATE_KEY = "request_id"


class RequestIdMiddleware:
    """각 HTTP request에 server-generated request ID를 부여한다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})[REQUEST_ID_STATE_KEY] = request_id
        token = current_request_id.set(request_id)
        started_at = time.perf_counter()
        status_code = 500
        logger.info("http_request_received")

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                if scope["path"].startswith("/api/"):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "http_request_completed method=%s status=%s response_time_ms=%s",
                scope["method"],
                status_code,
                max(0, int((time.perf_counter() - started_at) * 1000)),
            )
            current_request_id.reset(token)


def get_request_id(request: Request) -> str:
    """middleware가 생성한 현재 HTTP request ID를 반환한다."""

    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    if not isinstance(request_id, str) or not request_id:
        raise RuntimeError("RequestIdMiddleware가 등록되지 않았습니다.")
    return request_id
