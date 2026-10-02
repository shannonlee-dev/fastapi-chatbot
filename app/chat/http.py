"""Chat domain 오류를 HTML·JSON에서 공유하는 HTTP 의미로 변환한다."""

from app.chat.errors import (
    ChatError,
    ChatGenerationError,
    ChatQuotaError,
    ChatRateLimitError,
    ChatTimeoutError,
)
from app.core.errors import AppError


def chat_error_to_app_error(error: ChatError) -> AppError:
    """내부 예외 원문을 포함하지 않는 status·code·header를 반환한다."""

    if isinstance(error, ChatRateLimitError):
        return AppError(
            status_code=429,
            code=error.record_message,
            headers={"Retry-After": str(error.retry_after)},
        )
    if isinstance(error, ChatQuotaError):
        return AppError(status_code=503, code=error.record_message)
    if isinstance(error, ChatTimeoutError):
        return AppError(status_code=504, code=error.record_message)
    if isinstance(error, ChatGenerationError):
        return AppError(status_code=502, code=error.record_message)
    return AppError(status_code=500, code="internal_error")
