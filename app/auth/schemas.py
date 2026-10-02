"""인증된 사용자에 대한 안전한 read model이다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedUser:
    """보호된 화면에 제공하는 최소 사용자 정보다."""

    user_id: int
    is_admin: bool
