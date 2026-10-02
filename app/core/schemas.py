"""공통 HTTP 오류 schema다."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """모든 JSON 오류가 공유하는 안정된 형태다."""

    code: str
    detail: str
