"""HTML·JSON 요청의 공통 오류 응답을 처리한다."""

import logging
from collections.abc import Callable, Coroutine, Mapping
from typing import Any

from fastapi import Request, status
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from fastapi.exception_handlers import (
    request_validation_exception_handler as default_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from app.core.errors import AppError
from app.core.i18n import get_message
from app.core.request_id import REQUEST_ID_HEADER, get_request_id
from app.core.schemas import ErrorResponse

logger = logging.getLogger(__name__)


def get_exception_handlers() -> dict[
    int | type[Exception], Callable[[Request, Exception], Coroutine[Any, Any, Response]]
]:
    """공통 HTTP 오류 handler를 FastAPI 생성자에 전달할 mapping으로 묶는다."""

    return {
        RequestValidationError: validation_exception_handler,
        AppError: app_error_handler,
        HTTPException: http_exception_handler,
        Exception: unhandled_exception_handler,
    }


async def app_error_handler(request: Request, error: Exception) -> Response:
    """AppError를 locale-aware JSON 오류로 변환한다."""

    if not isinstance(error, AppError):
        return await unhandled_exception_handler(request, error)
    return _error_response(
        request=request,
        status_code=error.status_code,
        code=error.code,
        detail_key=error.detail_key,
        headers=error.headers,
    )


async def validation_exception_handler(request: Request, _error: Exception) -> Response:
    """Pydantic body 검증 실패를 내부 구조 없이 통일한다."""

    if not request.url.path.startswith("/api/"):
        if isinstance(_error, RequestValidationError):
            return await default_validation_exception_handler(request, _error)
        return await unhandled_exception_handler(request, _error)
    detail_key = _semantic_validation_detail_key(_error)
    if detail_key is not None:
        return _error_response(
            request=request,
            status_code=400,
            code="validation_error",
            detail_key=detail_key,
        )
    return _error_response(request=request, status_code=422, code="validation_error")


async def http_exception_handler(request: Request, error: Exception) -> Response:
    """Auth dependency의 HTTPException도 JSON API 오류 형식으로 통일한다."""

    if not isinstance(error, HTTPException):
        return await unhandled_exception_handler(request, error)
    if not request.url.path.startswith("/api/"):
        return await default_http_exception_handler(request, error)
    if error.status_code == status.HTTP_401_UNAUTHORIZED:
        return _error_response(
            request=request, status_code=401, code="not_authenticated"
        )
    if error.status_code == status.HTTP_403_FORBIDDEN:
        return _error_response(request=request, status_code=403, code="forbidden")
    codes = {404: "resource_not_found", 405: "method_not_allowed"}
    headers = dict(error.headers or {})
    if error.status_code == 405:
        route_path = getattr(request.scope.get("route"), "path", request.url.path)
        allowed_methods = getattr(request.app.state, "allowed_methods", {}).get(
            route_path
        )
        if allowed_methods:
            headers["Allow"] = ", ".join(sorted(allowed_methods))
    return _error_response(
        request=request,
        status_code=error.status_code,
        code=codes.get(error.status_code, "request_error"),
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, _error: Exception) -> Response:
    """예상하지 못한 예외를 안전한 내부 오류로 변환한다."""

    logger.error(
        "unhandled_error type=%s",
        type(_error).__name__,
        extra={"request_id": get_request_id(request)},
    )
    if not request.url.path.startswith("/api/"):
        response = HTMLResponse(
            "서버 오류가 발생했습니다.",
            status_code=500,
            headers={"Cache-Control": "no-store"},
        )
        response.headers[REQUEST_ID_HEADER] = get_request_id(request)
        return response
    response = _error_response(
        request=request,
        status_code=500,
        code="internal_error",
    )
    response.headers[REQUEST_ID_HEADER] = get_request_id(request)
    return response


def _semantic_validation_detail_key(error: Exception) -> str | None:
    """ChatRequest의 의미 검증 오류를 API detail key로 변환한다."""

    if not isinstance(error, RequestValidationError):
        return None
    detail_keys = {
        "empty_message": "empty_message",
        "message_too_long": "message_too_long",
    }
    for validation_error in error.errors():
        detail_key = detail_keys.get(validation_error["type"])
        if detail_key is not None:
            return detail_key
    return None


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    detail_key: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    detail = get_message(
        key=detail_key or code,
        accept_language=request.headers.get("accept-language"),
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, detail=detail).model_dump(),
        headers={"Cache-Control": "no-store", **(headers or {})},
    )
