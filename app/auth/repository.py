"""User persistence repository다."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import ADMIN_ROLE, USER_ROLE, User


class UserRepository(Protocol):
    """Auth Service가 사용하는 User persistence 계약이다."""

    def get_user_by_id(self, *, user_id: int) -> User | None:
        """ID가 일치하는 User를 반환한다."""

        ...

    def get_user_by_username(self, *, username: str) -> User | None:
        """username이 일치하는 User를 반환한다."""

        ...

    def get_admin_user(self) -> User | None:
        """관리자 역할을 가진 User 한 명을 반환한다."""

        ...

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str = USER_ROLE,
    ) -> User:
        """User를 추가하고 생성된 field를 사용할 수 있도록 flush한다."""

        ...


class SqlAlchemyUserRepository:
    """SQLAlchemy Session을 사용하는 UserRepository 구현체다."""

    def __init__(self, *, db: Session) -> None:
        self._db = db

    def get_user_by_id(self, *, user_id: int) -> User | None:
        return self._db.scalar(select(User).where(User.id == user_id))

    def get_user_by_username(self, *, username: str) -> User | None:
        return self._db.scalar(select(User).where(User.username == username))

    def get_admin_user(self) -> User | None:
        return self._db.scalar(
            select(User).where(User.role == ADMIN_ROLE).order_by(User.id).limit(1)
        )

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str = USER_ROLE,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
        )
        self._db.add(user)
        self._db.flush()
        return user
