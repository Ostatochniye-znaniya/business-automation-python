from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.users.models import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def head_name(self, department_id, role) -> str:
        person = await self.session.scalar(
            select(User)
            .where(User.department_id == department_id, User.role == role, User.is_active.is_(True))
            .order_by(User.id)
        )
        return person.full_name if person else "__________________"

    async def get_by_id(self, entity_id: int) -> User:
        entity = await self.session.get(User, entity_id)
        if entity is None:
            raise NotFoundError("User not found")
        return entity

    async def list_users(self, offset: int = 0, limit: int = 100) -> list[User]:
        return list((await self.session.scalars(select(User).offset(offset).limit(limit))).all())
