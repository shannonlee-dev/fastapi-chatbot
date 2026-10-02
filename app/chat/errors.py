"""Chat domain이 HTTP layer에 전달하는 안전한 오류다."""


class ChatError(Exception):
    """사용자 응답으로 변환 가능한 Chat domain 오류의 base class다."""


class ChatGenerationError(ChatError):
    """OpenAI 답변을 생성하지 못했다."""

    record_message = "openai_api_error"


class ChatTimeoutError(ChatGenerationError):
    """OpenAI 호출 시간이 초과됐다."""

    record_message = "openai_timeout"


class ChatRateLimitError(ChatGenerationError):
    """429 retry를 완료했거나 대기 시간이 허용 범위를 초과했다."""

    record_message = "openai_rate_limited"

    def __init__(self, *, retry_after: int = 1) -> None:
        self.retry_after = retry_after
        super().__init__(self.record_message)


class ChatQuotaError(ChatGenerationError):
    """Provider quota가 부족해 재시도로 해결할 수 없다."""

    record_message = "openai_quota_exceeded"


class ChatInvalidResponseError(ChatGenerationError):
    """OpenAI response에 사용할 수 있는 text answer가 없다."""

    record_message = "openai_api_error"


class ChatConfigurationError(ChatError):
    """OpenAI 호출에 필요한 server 설정이 없다."""


class ChatPersistenceError(ChatError):
    """ChatExchange read 또는 write transaction이 실패했다."""

    def __init__(self, *, is_write: bool = True) -> None:
        self.is_write = is_write
        super().__init__("write" if is_write else "read")
