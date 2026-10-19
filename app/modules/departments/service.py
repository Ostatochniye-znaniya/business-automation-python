from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.departments.models import Department


class DepartmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> Department:
        entity = await self.session.get(Department, entity_id)
        if entity is None:
            raise NotFoundError("Department not found")
        return entity

    async def list_departments(self, offset: int = 0, limit: int = 100) -> list[Department]:
        return list(
            (await self.session.scalars(select(Department).offset(offset).limit(limit))).all()
        )
