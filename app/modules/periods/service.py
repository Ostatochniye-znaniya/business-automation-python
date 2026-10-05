from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.periods.models import TestingPeriod
from app.modules.periods.schemas import TestingPeriodCreate


class PeriodService:
    """Use cases for testing periods. The write path owns its transaction."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, period_id: int) -> TestingPeriod:
        period = await self.session.get(TestingPeriod, period_id)
        if period is None:
            raise NotFoundError("TestingPeriod not found")
        return period

    async def list_periods(self, offset: int = 0, limit: int = 100) -> list[TestingPeriod]:
        statement = (
            select(TestingPeriod)
            .order_by(TestingPeriod.start_date.desc(), TestingPeriod.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.scalars(statement)).all())

    async def create_period(self, data: TestingPeriodCreate) -> TestingPeriod:
        period = TestingPeriod(**data.model_dump())
        self.session.add(period)
        await self.session.commit()
        await self.session.refresh(period)
        return period
