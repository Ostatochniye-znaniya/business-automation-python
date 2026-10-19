from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FeatureNotImplementedError, NotFoundError
from app.modules.reports.models import Report
from app.modules.reports.schemas import ReportStatistics


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> Report:
        entity = await self.session.get(Report, entity_id)
        if entity is None:
            raise NotFoundError("Report not found")
        return entity

    async def get_by_test(
        self, knowledge_test_id: int, offset: int = 0, limit: int = 100
    ) -> list[Report]:
        return list(
            (
                await self.session.scalars(
                    select(Report)
                    .where(Report.knowledge_test_id == knowledge_test_id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> ReportStatistics:
        """Unknown indicators are represented by null, never fabricated counts."""
        # TODO: agree period scope, required counts and report status rules with customer.
        return ReportStatistics()

    async def list_for_review(self) -> list[Report]:
        """Select reports after review statuses are agreed."""
        # TODO: customer must define which statuses require review.
        raise FeatureNotImplementedError("Review statuses are not agreed")

    async def upload_electronic(self, test_id: int, file_key: str) -> Report:
        """Reserved interface for report review."""
        # TODO: agree storage contract, reviewer permissions and status transitions.
        raise FeatureNotImplementedError("Report workflow is not agreed")

    async def approve_electronic(self, test_id: int) -> Report:
        """Reserved interface for report review."""
        # TODO: agree storage contract, reviewer permissions and status transitions.
        raise FeatureNotImplementedError("Report workflow is not agreed")

    async def reject_electronic(self, test_id: int, comment: str) -> Report:
        """Reserved interface for report review."""
        # TODO: agree storage contract, reviewer permissions and status transitions.
        raise FeatureNotImplementedError("Report workflow is not agreed")

    async def approve_paper(self, test_id: int) -> Report:
        """Reserved interface for report review."""
        # TODO: agree storage contract, reviewer permissions and status transitions.
        raise FeatureNotImplementedError("Report workflow is not agreed")

    async def reject_paper(self, test_id: int, comment: str) -> Report:
        """Reserved interface for report review."""
        # TODO: agree storage contract, reviewer permissions and status transitions.
        raise FeatureNotImplementedError("Report workflow is not agreed")
