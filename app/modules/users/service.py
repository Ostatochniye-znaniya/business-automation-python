from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> User:
        entity = await self.session.get(User, entity_id)
        if entity is None:
            raise NotFoundError("User not found")
        return entity

    async def list_users(self, offset: int = 0, limit: int = 100) -> list[User]:
        return list((await self.session.scalars(select(User).offset(offset).limit(limit))).all())

    async def update_user(self, entity_id: int, data: UserUpdate) -> User:
        entity = await self.get_by_id(entity_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
