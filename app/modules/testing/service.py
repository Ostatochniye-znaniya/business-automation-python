from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.testing.models import KnowledgeTest
from app.modules.testing.schemas import KnowledgeTestCreate


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
