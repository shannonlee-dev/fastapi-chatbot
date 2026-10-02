"""Auth use case의 HTTP에 독립적인 domain 오류다."""

from enum import StrEnum


class RegistrationReason(StrEnum):
    """회원가입이 실패한 안전한 domain reason이다."""

    USERNAME_LENGTH = "username_length"
    PASSWORD_LENGTH = "password_length"
    DUPLICATE_USERNAME = "duplicate_username"


class RegistrationError(Exception):
    """UI가 안전한 회원가입 오류 message로 변환할 수 있는 예외다."""

    def __init__(self, reason: RegistrationReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class AdminBootstrapReason(StrEnum):
    """Initial admin 생성이 실패한 안전한 startup reason이다."""

    MISSING_INITIAL_PASSWORD = "missing_initial_password"
    INVALID_INITIAL_PASSWORD = "invalid_initial_password"
    INVALID_ADMIN_ROLE = "invalid_admin_role"
    DB_ERROR = "db_error"


class AdminBootstrapError(RuntimeError):
    """Application startup을 중단하는 안전한 initial admin 오류다."""

    def __init__(self, reason: AdminBootstrapReason) -> None:
        self.reason = reason
        super().__init__(reason.value)
