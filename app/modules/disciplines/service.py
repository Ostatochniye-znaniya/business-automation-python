from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.disciplines.models import Discipline
from app.modules.disciplines.schemas import DashboardStatistics


class DisciplineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> Discipline:
        entity = await self.session.get(Discipline, entity_id)
        if entity is None:
            raise NotFoundError("Discipline not found")
        return entity

    async def list_disciplines(self, offset: int = 0, limit: int = 100) -> list[Discipline]:
        return list(
            (await self.session.scalars(select(Discipline).offset(offset).limit(limit))).all()
        )

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> DashboardStatistics:
        """Unknown indicators are represented by null, never fabricated counts."""
        # TODO: agree period scope, required counts and report status rules with customer.
        return DashboardStatistics()
