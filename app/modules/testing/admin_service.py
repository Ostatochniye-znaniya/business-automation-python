from datetime import UTC

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import KnowledgeTestStatus, UserRole
from app.core.exceptions import NotFoundError
from app.core.permissions import require_role
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup
from app.modules.periods.models import TestingPeriod
from app.modules.reports.models import Report
from app.modules.testing.models import KnowledgeTest
from app.modules.testing.schemas import AdminCheckRead, AdminChecksPage
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


def _stage(test: KnowledgeTest, electronic_status: str, paper_status: str) -> str:
    if test.status == KnowledgeTestStatus.CANCELLED:
        return "Проверка отменена"
    if test.status == KnowledgeTestStatus.COMPLETED:
        if electronic_status == "REJECTED":
            return "Ожидает исправления электронного отчёта"
        if electronic_status == "SUBMITTED":
            return "Ожидает проверки электронного отчёта"
        if electronic_status != "APPROVED":
            return "Ожидает загрузки электронного отчёта"
        if paper_status == "REJECTED":
            return "Ожидает исправления бумажного отчёта"
        if paper_status not in {"APPROVED", "NOT_REQUIRED"}:
            return "Ожидает сдачи и проверки бумажного отчёта"
        return "Все отчёты приняты"
    if test.teacher_id is None:
        return "Ожидает назначения преподавателя"
    if test.scheduled_at is None:
        return "Ожидает назначения даты"
    if test.agreement_status == "REJECTED":
        return "Ожидает нового предложения даты"
    if test.agreement_status != "AGREED":
        return "Ожидает согласования даты"
    if test.status == KnowledgeTestStatus.IN_PROGRESS:
        return "Ожидает завершения ведомости"
    return "Ожидает проведения проверки"


class AdminCheckService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _query():
        return (
            select(
                KnowledgeTest,
                StudyGroup.name,
                Discipline.name,
                TestingPeriod,
                User.full_name,
                Report,
            )
            .select_from(KnowledgeTest)
            .join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id)
            .join(Discipline, Discipline.id == KnowledgeTest.discipline_id)
            .join(TestingPeriod, TestingPeriod.id == KnowledgeTest.period_id)
            .outerjoin(User, User.id == KnowledgeTest.teacher_id)
            .outerjoin(Report, Report.knowledge_test_id == KnowledgeTest.id)
        )

    @staticmethod
    def _read(
        test: KnowledgeTest,
        group_name: str,
        discipline_name: str,
        period: TestingPeriod,
        teacher_name: str | None,
        report: Report | None,
    ) -> AdminCheckRead:
        electronic_status = (report.electronic_status if report else None) or "MISSING"
        paper_status = (report.paper_status if report else None) or "MISSING"
        if not period.paper_reports_required:
            paper_status = "NOT_REQUIRED"
        return AdminCheckRead(
            id=test.id,
            group_name=group_name,
            discipline_name=discipline_name,
            period_name=period.name,
            period_status=period.status,
            teacher_name=teacher_name,
            scheduled_at=test.scheduled_at.replace(tzinfo=UTC) if test.scheduled_at else None,
            room=test.room,
            status=test.status,
            agreement_status=test.agreement_status,
            agreement_comment=test.agreement_comment,
            electronic_status=electronic_status,
            paper_status=paper_status,
            electronic_comment=report.electronic_comment if report else None,
            paper_comment=report.paper_comment if report else None,
            stage=_stage(test, electronic_status, paper_status),
        )

    async def list_checks(
        self,
        actor: UserRead,
        *,
        search: str | None,
        period_id: int | None,
        status: KnowledgeTestStatus | None,
        offset: int,
        limit: int,
    ) -> AdminChecksPage:
        require_role(actor, {UserRole.ADMIN})
        query = self._query()
        if search and (term := search.strip().lower()):
            query = query.where(
                or_(
                    func.lower(StudyGroup.name).contains(term, autoescape=True),
                    func.lower(Discipline.name).contains(term, autoescape=True),
                )
            )
        if period_id is not None:
            query = query.where(KnowledgeTest.period_id == period_id)
        if status is not None:
            query = query.where(KnowledgeTest.status == status)
        total = await self.session.scalar(query.with_only_columns(func.count()))
        result = await self.session.execute(
            query.order_by(KnowledgeTest.id.desc()).offset(offset).limit(limit)
        )
        return AdminChecksPage(items=[self._read(*row) for row in result], total=total or 0)

    async def get_check(self, actor: UserRead, check_id: int) -> AdminCheckRead:
        require_role(actor, {UserRole.ADMIN})
        result = await self.session.execute(self._query().where(KnowledgeTest.id == check_id))
        row = result.one_or_none()
        if row is None:
            raise NotFoundError("Проверка не найдена")
        return self._read(*row)
