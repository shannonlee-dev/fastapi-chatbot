"""Auth use case와 User transaction을 처리한다."""

from __future__ import annotations

import logging
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.auth.errors import (
    AdminBootstrapError,
    AdminBootstrapReason,
    RegistrationError,
    RegistrationReason,
)
from app.auth.models import ADMIN_ROLE, User
from app.auth.repository import UserRepository
from app.auth.schemas import AuthenticatedUser
from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.core.transactions import Transaction

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72

logger = logging.getLogger(__name__)


class AuthService:
    """사용자 인증·등록·초기화와 transaction을 처리한다."""

    def __init__(self, *, db: Transaction, repository: UserRepository) -> None:
        self._db = db
        self._repository = repository

    def get_authenticated_user(self, *, user_id: int) -> AuthenticatedUser | None:
        """실제 사용자 record를 화면용 최소 정보로 변환한다."""

        user = self._repository.get_user_by_id(user_id=user_id)
        if user is None:
            return None
        return AuthenticatedUser(user_id=user.id, is_admin=user.role == ADMIN_ROLE)

    def authenticate_user(
        self,
        *,
        username: str,
        password: str,
    ) -> User | None:
        """Username과 password가 일치하는 User를 반환한다."""

        user = self._repository.get_user_by_username(username=username.strip())
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    def register_user(self, *, username: str, password: str) -> User:
        """회원가입 입력을 검증하고 일반 사용자 계정을 저장한다."""

        normalized_username = username.strip()
        _validate_registration_input(
            username=normalized_username,
            password=password,
        )

        try:
            if (
                self._repository.get_user_by_username(username=normalized_username)
                is not None
            ):
                raise RegistrationError(RegistrationReason.DUPLICATE_USERNAME)

            user = self._repository.create_user(
                username=normalized_username,
                password_hash=hash_password(password),
            )
            self._db.commit()
        except RegistrationError:
            self._db.rollback()
            raise
        except IntegrityError:
            self._db.rollback()
            raise RegistrationError(RegistrationReason.DUPLICATE_USERNAME) from None
        except Exception:
            self._db.rollback()
            raise

        return user

    def ensure_initial_admin(self, *, app_settings: Settings) -> None:
        """초기 admin 계정을 필요할 때 한 번만 생성한다."""

        try:
            existing_admin = self._repository.get_admin_user()
        except Exception:  # noqa: BLE001 - startup 경계에서 내부 DB 오류를 숨긴다.
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.DB_ERROR)

        if existing_admin is not None:
            self._db.rollback()
            return

        try:
            bootstrap_username_owner = self._repository.get_user_by_username(
                username=app_settings.admin_username,
            )
        except Exception:  # noqa: BLE001 - startup 경계에서 내부 DB 오류를 숨긴다.
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.DB_ERROR)

        if bootstrap_username_owner is not None:
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.INVALID_ADMIN_ROLE)

        initial_password = app_settings.admin_initial_password
        if initial_password is None:
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.MISSING_INITIAL_PASSWORD)

        password = initial_password.get_secret_value()
        if not _is_valid_password_length(password):
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.INVALID_INITIAL_PASSWORD)

        try:
            self._repository.create_user(
                username=app_settings.admin_username,
                password_hash=hash_password(password),
                role=ADMIN_ROLE,
            )
            self._db.commit()
        except Exception:  # noqa: BLE001 - startup 경계에서 내부 DB·hash 오류를 숨긴다.
            self._db.rollback()
            _raise_admin_bootstrap_error(AdminBootstrapReason.DB_ERROR)


def _validate_registration_input(*, username: str, password: str) -> None:
    if not MIN_USERNAME_LENGTH <= len(username) <= MAX_USERNAME_LENGTH:
        raise RegistrationError(RegistrationReason.USERNAME_LENGTH)
    if not _is_valid_password_length(password):
        raise RegistrationError(RegistrationReason.PASSWORD_LENGTH)


def _is_valid_password_length(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def _raise_admin_bootstrap_error(reason: AdminBootstrapReason) -> NoReturn:
    logger.error("admin_bootstrap_failed reason=%s", reason.value)
    raise AdminBootstrapError(reason) from None
