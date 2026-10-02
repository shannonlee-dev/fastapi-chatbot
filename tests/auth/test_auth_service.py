"""DB 구현 없이 Auth Service의 주입된 계약과 안전한 read model을 검증한다."""

from __future__ import annotations

import pytest

from app.auth.models import ADMIN_ROLE, USER_ROLE, User
from app.auth.schemas import AuthenticatedUser
from app.auth.service import AuthService
from app.core.security import verify_password


class RecordingTransaction:
    """실제 DB 대신 transaction 완료 순서를 기록한다."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


class MemoryUserRepository:
    """UserRepository 계약을 DB 없이 제공한다."""

    def __init__(self, user: User | None = None) -> None:
        self.user = user

    def get_user_by_id(self, *, user_id: int) -> User | None:
        return self.user if self.user is not None and self.user.id == user_id else None

    def get_user_by_username(self, *, username: str) -> User | None:
        return (
            self.user
            if self.user is not None and self.user.username == username
            else None
        )

    def get_admin_user(self) -> User | None:
        return (
            self.user
            if self.user is not None and self.user.role == ADMIN_ROLE
            else None
        )

    def create_user(
        self, *, username: str, password_hash: str, role: str = USER_ROLE
    ) -> User:
        self.user = User(
            id=1, username=username, password_hash=password_hash, role=role
        )
        return self.user


@pytest.mark.parametrize("role", [USER_ROLE, ADMIN_ROLE])
def test_authenticated_user_contains_only_safe_display_fields(role: str) -> None:
    transaction = RecordingTransaction()
    repository = MemoryUserRepository(
        User(id=7, username="user", password_hash="secret", role=role)
    )
    service = AuthService(db=transaction, repository=repository)

    result = service.get_authenticated_user(user_id=7)

    assert result == AuthenticatedUser(user_id=7, is_admin=role == ADMIN_ROLE)
    assert result is not repository.user
    assert result is not None
    assert not hasattr(result, "password_hash")
    assert not hasattr(result, "username")
    assert transaction.events == []


def test_authenticated_user_returns_none_for_missing_record() -> None:
    service = AuthService(db=RecordingTransaction(), repository=MemoryUserRepository())

    assert service.get_authenticated_user(user_id=7) is None


def test_registration_uses_injected_repository_and_transaction() -> None:
    transaction = RecordingTransaction()
    repository = MemoryUserRepository()
    service = AuthService(db=transaction, repository=repository)

    user = service.register_user(username="  new-user  ", password="password")

    assert user is repository.user
    assert user.username == "new-user"
    assert user.role == USER_ROLE
    assert verify_password("password", user.password_hash)
    assert transaction.events == ["commit"]
