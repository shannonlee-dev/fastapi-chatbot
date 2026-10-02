"""Auth의 공개 진입점과 production 의존성을 조립한다."""

from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.repository import SqlAlchemyUserRepository
from app.auth.schemas import AuthenticatedUser
from app.auth.service import AuthService
from app.core.config import Settings


def _create_service(db: Session) -> AuthService:
    return AuthService(db=db, repository=SqlAlchemyUserRepository(db=db))


def authenticate_user(*, db: Session, username: str, password: str) -> User | None:
    """Username과 password가 일치하는 사용자를 반환한다."""

    return _create_service(db).authenticate_user(username=username, password=password)


def register_user(*, db: Session, username: str, password: str) -> User:
    """일반 사용자 계정을 검증하고 저장한다."""

    return _create_service(db).register_user(username=username, password=password)


def ensure_initial_admin(*, db: Session, app_settings: Settings) -> None:
    """설정에 따라 초기 관리자 계정을 준비한다."""

    _create_service(db).ensure_initial_admin(app_settings=app_settings)


def get_authenticated_user(*, db: Session, user_id: int) -> AuthenticatedUser | None:
    """실제 사용자 record에 대응하는 최소 인증 정보를 반환한다."""

    return _create_service(db).get_authenticated_user(user_id=user_id)
