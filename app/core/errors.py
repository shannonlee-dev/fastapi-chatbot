"""HTTP 표현 layer가 사용하는 공통 application 오류다."""


class AppError(Exception):
    """JSON API가 안전하게 응답할 수 있는 application 오류다."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        detail_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.detail_key = detail_key or code
        self.headers = headers or {}
        super().__init__(code)
