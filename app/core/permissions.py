"""Small role and department checks shared by module use cases."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.modules.users.models import AuditEvent
from app.modules.users.schemas import UserRead

MANAGERS = {UserRole.ADMIN, UserRole.LPR}
PLANNERS = MANAGERS | {UserRole.CHAIR_HEAD, UserRole.DEPARTMENT_RESPONSIBLE}


def require_role(actor: UserRead, roles: set[UserRole]) -> None:
    if not actor.is_active or actor.role not in roles:
        raise ForbiddenError("Недостаточно прав для выполнения операции")


async def require_department(session: AsyncSession, actor: UserRead, department_id: int | None):
    if actor.role in MANAGERS:
        return
    from app.modules.departments.service import DepartmentService

    ids = await DepartmentService(session).subtree_ids(actor.department_id)
    if department_id is None or department_id not in ids:
        raise ForbiddenError("Данные относятся к другому подразделению")


def audit(session: AsyncSession, actor: UserRead, action: str, entity_id: int | None = None):
    session.add(
        AuditEvent(
            actor_id=actor.id,
            action=action,
            entity_id=entity_id,
            details={},
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
