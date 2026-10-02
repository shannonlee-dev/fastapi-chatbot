"""Admin의 공개 진입점과 production 의존성을 조립한다."""

from sqlalchemy.orm import Session

from app.admin.repository import SqlAlchemyAdminRepository
from app.admin.schemas import AdminChatOperationMetadataItem
from app.admin.service import AdminService


def list_admin_chat_operation_metadata(
    *, db: Session
) -> list[AdminChatOperationMetadataItem]:
    """관리자에게 공개할 수 있는 Chat 운영 metadata를 반환한다."""

    service = AdminService(db=db, repository=SqlAlchemyAdminRepository(db=db))
    return service.list_admin_chat_operation_metadata()
