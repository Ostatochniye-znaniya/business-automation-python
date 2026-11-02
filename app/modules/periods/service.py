from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TestingPeriodStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import moscow_today
from app.modules.groups.models import GroupPeriod
from app.modules.groups.recommendation_models import GroupRecommendation
from app.modules.orders.models import Order
from app.modules.periods.models import TestingPeriod
from app.modules.periods.schemas import TestingPeriodCreate
from app.modules.testing.models import GroupParticipation, KnowledgeTest


class PeriodService:
    """Use cases for testing periods. The write path owns its transaction."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, period_id: int) -> TestingPeriod:
        period = await self.session.get(TestingPeriod, period_id)
        if period is None:
            raise NotFoundError("TestingPeriod not found")
        return period

    async def require_editable(self, period_id: int) -> TestingPeriod:
        period = await self.session.get(TestingPeriod, period_id, with_for_update=True)
        if period is None:
            raise NotFoundError("Период не найден")
        if (
            period.status != TestingPeriodStatus.OPEN
            or not period.start_date <= moscow_today() <= period.end_date
        ):
            raise ConflictError("Редактирование периода закрыто: обратитесь к ЛПР")
        return period

    async def list_periods(self, offset: int = 0, limit: int = 100) -> list[TestingPeriod]:
        statement = (
            select(TestingPeriod)
            .order_by(TestingPeriod.start_date.desc(), TestingPeriod.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.scalars(statement)).all())

    async def create_period(self, data: TestingPeriodCreate, actor) -> TestingPeriod:
        from app.core.permissions import MANAGERS, require_role

        require_role(actor, MANAGERS)
        period = TestingPeriod(**data.model_dump())
        self.session.add(period)
        await self.session.commit()
        await self.session.refresh(period)
        return period

    async def update(self, period_id, data, actor):
        from app.core.permissions import MANAGERS, audit, require_role

        require_role(actor, MANAGERS)
        period = await self.get_by_id(period_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(period, key, value)
        from app.modules.reports.service import ReportService

        await ReportService(self.session).refresh_period_completion(period)
        audit(self.session, actor, "period.update", period_id)
        await self.session.commit()
        return period

    async def delete(self, period_id: int, actor) -> None:
        from app.core.permissions import MANAGERS, audit, require_role

        require_role(actor, MANAGERS)
        period = await self.session.get(TestingPeriod, period_id, with_for_update=True)
        if period is None:
            raise NotFoundError("Период не найден")

        links = (
            (KnowledgeTest, "тестирования"),
            (GroupParticipation, "участие групп"),
            (GroupPeriod, "группы периода"),
            (GroupRecommendation, "рекомендации групп"),
            (Order, "приказы"),
        )
        for model, label in links:
            linked = await self.session.scalar(
                select(model).where(model.period_id == period_id).limit(1)
            )
            if linked is not None:
                raise ConflictError(f"Нельзя удалить период: есть связанные {label}")

        await self.session.delete(period)
        audit(self.session, actor, "period.delete", period_id)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError("Нельзя удалить период: есть связанные данные") from error

    async def set_report_policy(self, period_id: int, required: bool, actor) -> TestingPeriod:
        from app.core.permissions import MANAGERS, audit, require_role
        from app.modules.reports.service import ReportService

        require_role(actor, MANAGERS)
        period = await self.session.get(TestingPeriod, period_id, with_for_update=True)
        if period is None:
            raise NotFoundError("Период не найден")
        period.paper_reports_required = required
        await ReportService(self.session).refresh_period_completion(period)
        audit(self.session, actor, "period.report_policy", period_id)
        await self.session.commit()
        return period
