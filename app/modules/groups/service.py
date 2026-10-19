from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.groups.models import StudyGroup
from app.modules.groups.schemas import DashboardStatistics


class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> StudyGroup:
        entity = await self.session.get(StudyGroup, entity_id)
        if entity is None:
            raise NotFoundError("StudyGroup not found")
        return entity

    async def list_groups(self, offset: int = 0, limit: int = 100) -> list[StudyGroup]:
        return list(
            (await self.session.scalars(select(StudyGroup).offset(offset).limit(limit))).all()
        )

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> DashboardStatistics:
        """Unknown indicators are represented by null, never fabricated counts."""
        # TODO: agree period scope, required counts and report status rules with customer.
        return DashboardStatistics()
