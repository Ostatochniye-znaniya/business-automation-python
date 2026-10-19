import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.modules.users.models import DevSession, User


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def require_development(settings: Settings) -> None:
        if settings.APP_ENV not in {"development", "test"}:
            raise ForbiddenError("Локальный вход отключён в production")

    async def development_users(self, settings: Settings) -> list[User]:
        self.require_development(settings)
        return list(
            (
                await self.session.scalars(
                    select(User).where(User.is_active.is_(True)).order_by(User.full_name).limit(100)
                )
            ).all()
        )

    async def login(self, user_id: int, settings: Settings) -> tuple[User, str]:
        self.require_development(settings)
        user = await self.session.get(User, user_id)
        if user is None or not user.is_active:
            raise ForbiddenError("Доступ пользователя отключён")
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC).replace(tzinfo=None)
        await self.session.execute(delete(DevSession).where(DevSession.expires_at < now))
        self.session.add(
            DevSession(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user.id,
                expires_at=now + timedelta(hours=8),
            )
        )
        await self.session.commit()
        return user, token

    async def logout(self, token: str | None) -> None:
        if token:
            await self.session.execute(
                delete(DevSession).where(
                    DevSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            )
            await self.session.commit()
