from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.departments.models import Department
from app.modules.users.models import AccessRequest, AuditEvent, ImportLog, User
from app.modules.users.schemas import AccessDecision, AccessRequestCreate, UserCreate, UserRead


async def current_user(actor: UserRead):
    return actor


async def users(session: AsyncSession, actor: UserRead, offset: int = 0, limit: int = 100):
    require_role(actor, MANAGERS)
    return list(
        (
            await session.scalars(
                select(User).order_by(User.full_name, User.id).offset(max(0, offset)).limit(limit)
            )
        ).all()
    )


async def save_user(session: AsyncSession, actor: UserRead, data: UserCreate, user_id=None):
    require_role(actor, MANAGERS)
    if actor.role != UserRole.ADMIN and data.role == UserRole.ADMIN:
        raise ValidationError("Назначать администратора может только администратор")
    user = await session.get(User, user_id) if user_id else User()
    if user is None:
        raise NotFoundError("Сотрудник не найден")
    if user_id == actor.id and (not data.is_active or data.role != actor.role):
        raise ConflictError("Нельзя отключить собственный доступ")
    if user_id and user.role == UserRole.ADMIN and (actor.role != UserRole.ADMIN):
        raise ValidationError("Изменять администратора может только администратор")
    if data.department_id and await session.get(Department, data.department_id) is None:
        raise NotFoundError("Подразделение не найдено")
    if data.external_id and await session.scalar(
        select(User.id).where(User.external_id == data.external_id, User.id != (user_id or 0))
    ):
        raise ConflictError("Табельный номер уже используется")
    for key, value in data.model_dump().items():
        setattr(user, key, value)
    session.add(user)
    await session.flush()
    audit(session, actor, "user.save", user.id)
    await session.commit()
    return user


async def create_user(data: UserCreate, session: AsyncSession, actor: UserRead):
    return await save_user(session, actor, data)


async def update_user(user_id: int, data: UserCreate, session: AsyncSession, actor: UserRead):
    return await save_user(session, actor, data, user_id)


async def deactivate_user(user_id: int, session: AsyncSession, actor: UserRead):
    require_role(actor, MANAGERS)
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Сотрудник не найден")
    data = UserCreate.model_validate(UserRead.model_validate(user).model_dump(exclude={"id"}))
    data.is_active = False
    await save_user(session, actor, data, user_id)


async def request_access(data: AccessRequestCreate, session: AsyncSession, actor: UserRead):
    if data.requested_role == UserRole.GUEST:
        raise ValidationError("Выберите рабочую роль")
    if await session.scalar(
        select(AccessRequest.id).where(
            AccessRequest.user_id == actor.id, AccessRequest.status == "PENDING"
        )
    ):
        raise ConflictError("Запрос уже ожидает рассмотрения")
    request = AccessRequest(
        user_id=actor.id,
        requested_role=data.requested_role,
        reason=data.reason,
        requested_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(request)
    audit(session, actor, "access.request")
    await session.commit()
    return request


async def access_requests(
    session: AsyncSession, actor: UserRead, offset: int = 0, limit: int = 100
):
    require_role(actor, MANAGERS)
    return list(
        (
            await session.scalars(
                select(AccessRequest)
                .order_by(AccessRequest.id.desc())
                .offset(max(0, offset))
                .limit(limit)
            )
        ).all()
    )


async def decide_access(
    request_id: int, data: AccessDecision, session: AsyncSession, actor: UserRead
):
    require_role(actor, MANAGERS)
    request = await session.get(AccessRequest, request_id, with_for_update=True)
    if request is None:
        raise NotFoundError("Запрос не найден")
    if request.status != "PENDING":
        raise ConflictError("Запрос уже рассмотрен")
    user = await session.get(User, request.user_id)
    if user.role == UserRole.ADMIN and actor.role != UserRole.ADMIN:
        raise ValidationError("Изменять администратора может только администратор")
    if data.approved and user.id == actor.id and request.requested_role != actor.role:
        raise ConflictError("Нельзя менять собственную роль через заявку")
    if data.approved:
        if request.requested_role == UserRole.ADMIN and actor.role != UserRole.ADMIN:
            raise ValidationError("Назначать администратора может только администратор")
        user.role = UserRole(request.requested_role)
    request.status = "APPROVED" if data.approved else "REJECTED"
    request.processed_by_id = actor.id
    request.processed_at = datetime.now(UTC).replace(tzinfo=None)
    audit(session, actor, "access.decide", request.id)
    await session.commit()
    return request


async def audit_events(session: AsyncSession, actor: UserRead, offset: int = 0, limit: int = 100):
    require_role(actor, MANAGERS)
    return list(
        (
            await session.scalars(
                select(AuditEvent)
                .order_by(AuditEvent.id.desc())
                .offset(max(0, offset))
                .limit(limit)
            )
        ).all()
    )


async def import_logs(session: AsyncSession, actor: UserRead):
    require_role(actor, MANAGERS)
    return list(
        (await session.scalars(select(ImportLog).order_by(ImportLog.id.desc()).limit(100))).all()
    )
