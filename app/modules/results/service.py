from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FeatureNotImplementedError, NotFoundError
from app.modules.results.models import TestResult
from app.modules.results.schemas import TestResultCreate


class ResultService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> TestResult:
        entity = await self.session.get(TestResult, entity_id)
        if entity is None:
            raise NotFoundError("TestResult not found")
        return entity

    async def get_by_test(
        self, knowledge_test_id: int, offset: int = 0, limit: int = 100
    ) -> list[TestResult]:
        return list(
            (
                await self.session.scalars(
                    select(TestResult)
                    .where(TestResult.knowledge_test_id == knowledge_test_id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def save_result(self, data: TestResultCreate) -> TestResult:
        """Save after grading scale and duplicate handling are agreed."""
        # TODO: agree score ranges and rules for replacing an existing result.
        raise FeatureNotImplementedError("Result saving rules are not agreed")
