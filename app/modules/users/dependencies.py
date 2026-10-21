from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.core.security import authenticate_token
from app.db.dependencies import get_db_session
from app.modules.users.models import DevSession, User
from app.modules.users.schemas import UserRead


async def get_dev_user(settings: Annotated[Settings, Depends(get_settings)]) -> UserRead:
    """Opt-in development identity; never allowed outside development."""
    if settings.APP_ENV != "development":
        raise ForbiddenError("Development identity is disabled")
    return UserRead(id=1, full_name="Development user", role=UserRole.GUEST)


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
    dev_session: Annotated[str | None, Cookie()] = None,
) -> UserRead:
    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ForbiddenError("Требуется Bearer-токен")
        actor = await authenticate_token(token)
        user = await session.scalar(select(User).where(User.external_id == actor.external_id))
        if user is None:
            raise ForbiddenError("Сотрудник отсутствует в справочнике: обратитесь к администратору")
        actor = UserRead.model_validate(user)
    else:
        user = None
        if settings.APP_ENV in {"development", "test"}:
            if dev_session:
                import hashlib
                from datetime import UTC, datetime

                login = await session.get(
                    DevSession, hashlib.sha256(dev_session.encode()).hexdigest()
                )
                if login and login.expires_at > datetime.now(UTC).replace(tzinfo=None):
                    user = await session.get(User, login.user_id)
            elif settings.DEV_USER_ID is not None:
                user = await session.get(User, settings.DEV_USER_ID)
        if user is None:
            raise ForbiddenError("Войдите в систему для выполнения операции")
        actor = UserRead.model_validate(user)
    if not actor.is_active:
        raise ForbiddenError("Доступ пользователя отключён")
    return actor


async def require_staff(actor: Annotated[UserRead, Depends(get_current_user)]):
    if actor.role == UserRole.GUEST:
        raise ForbiddenError("Дождитесь назначения роли")
    return actor


async def require_manager(actor: Annotated[UserRead, Depends(get_current_user)]):
    from app.core.permissions import MANAGERS, require_role

    require_role(actor, MANAGERS)
    return actor
