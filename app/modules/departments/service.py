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

    async def subtree_ids(self, department_id: int | None) -> set[int]:
        """Resolve descendants and tolerate incomplete external hierarchies."""
        if department_id is None:
            return set()
        pairs = (await self.session.execute(select(Department.id, Department.parent_id))).all()
        ids = {department_id}
        while new_ids := {identifier for identifier, parent in pairs if parent in ids} - ids:
            ids.update(new_ids)
        return ids
