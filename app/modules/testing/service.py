from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup
from app.modules.periods.models import TestingPeriod
from app.modules.testing.models import KnowledgeTest
from app.modules.testing.schemas import KnowledgeTestCreate
from app.modules.users.models import User


class TestingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> KnowledgeTest:
        entity = await self.session.get(KnowledgeTest, entity_id)
        if entity is None:
            raise NotFoundError("KnowledgeTest not found")
        return entity

    async def list_by_period(
        self, period_id: int, offset: int = 0, limit: int = 100
    ) -> list[KnowledgeTest]:
        return list(
            (
                await self.session.scalars(
                    select(KnowledgeTest)
                    .where(KnowledgeTest.period_id == period_id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def create(self, data: KnowledgeTestCreate) -> KnowledgeTest:
        for model, entity_id in (
            (StudyGroup, data.group_id),
            (TestingPeriod, data.period_id),
            (Discipline, data.discipline_id),
            (User, data.teacher_id),
        ):
            if entity_id is not None and await self.session.get(model, entity_id) is None:
                raise NotFoundError(f"{model.__name__} not found")
        if await self.session.get(GroupPeriod, (data.group_id, data.period_id)) is None:
            self.session.add(GroupPeriod(group_id=data.group_id, period_id=data.period_id))
        entity = KnowledgeTest(**data.model_dump())
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update_schedule(self, test_id: int, scheduled_at: datetime | None) -> KnowledgeTest:
        entity = await self.get_by_id(test_id)
        entity.scheduled_at = scheduled_at
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
