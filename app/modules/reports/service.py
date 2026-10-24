from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import KnowledgeTestStatus, UserRole
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.reports.models import Report
from app.modules.reports.schemas import ReportMetadata, ReportStatistics
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.schemas import UserRead


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def metadata(self, report_id: int, data: ReportMetadata, actor: UserRead) -> Report:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        report = await self.get_by_id(report_id)
        await TestingWorkflow(self.session).get_test(report.knowledge_test_id, actor, write=True)
        if report.electronic_status in {"SUBMITTED", "APPROVED"}:
            raise ConflictError("Отзовите отчёт перед редактированием")
        report.previous_teacher_name = data.previous_teacher_name
        audit(self.session, actor, "report.metadata", report.id)
        await self.session.commit()
        return report

    async def delete(self, report_id: int, actor: UserRead) -> None:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        report = await self.get_by_id(report_id)
        await TestingWorkflow(self.session).get_test(report.knowledge_test_id, actor, write=True)
        if report.electronic_status not in {"DRAFT", "REJECTED"}:
            raise ConflictError("Сначала отзовите отчёт с проверки")
        await self.session.delete(report)
        audit(self.session, actor, "report.delete", report_id)
        await self.session.commit()

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

    async def create(self, test_id: int, actor: UserRead) -> Report:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        test = await TestingWorkflow(self.session).get_test(test_id, actor, write=True)
        existing = await self.get_by_test(test_id)
        if existing:
            return existing[0]
        if test.status != KnowledgeTestStatus.COMPLETED:
            raise ConflictError("Сначала завершите заполнение результатов проверки")
        report = Report(
            knowledge_test_id=test.id,
            electronic_status="DRAFT",
            paper_status="MISSING",
            final_status="PENDING",
        )
        self.session.add(report)
        await self.session.flush()
        audit(self.session, actor, "report.create", report.id)
        await self.session.commit()
        return report

    async def list_for_review(
        self,
        actor: UserRead,
        period_id: int | None = None,
        faculty_id: int | None = None,
        group_id: int | None = None,
        discipline_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Report]:
        require_role(actor, MANAGERS)
        from app.modules.departments.service import DepartmentService
        from app.modules.groups.models import StudyGroup
        from app.modules.testing.models import KnowledgeTest

        query = select(Report).join(KnowledgeTest, KnowledgeTest.id == Report.knowledge_test_id)
        if period_id:
            query = query.where(KnowledgeTest.period_id == period_id)
        if group_id:
            query = query.where(KnowledgeTest.group_id == group_id)
        if discipline_id:
            query = query.where(KnowledgeTest.discipline_id == discipline_id)
        if faculty_id:
            ids = await DepartmentService(self.session).subtree_ids(faculty_id)
            query = query.join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id).where(
                StudyGroup.department_id.in_(ids)
            )
        return list(
            (
                await self.session.scalars(
                    query.order_by(Report.id.desc()).offset(offset).limit(limit)
                )
            ).all()
        )

    async def upload_electronic(
        self, report_id: int, filename: str, content: bytes, actor: UserRead
    ) -> Report:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        report = await self.get_by_id(report_id)
        test = await TestingWorkflow(self.session).get_test(
            report.knowledge_test_id, actor, write=True
        )
        if test.status != KnowledgeTestStatus.COMPLETED:
            raise ConflictError("Сначала завершите проверку")
        if report.electronic_status == "APPROVED":
            raise ConflictError("Одобренный отчёт необходимо отозвать перед заменой файла")
        from starlette.concurrency import run_in_threadpool

        from app.modules.reports.files import save_file, storage_path

        key = await run_in_threadpool(save_file, filename, content)
        report.electronic_file_key = key
        report.electronic_status = "SUBMITTED"
        report.electronic_comment = None
        report.paper_status = "MISSING"
        report.paper_comment = None
        report.final_status = "PENDING"
        audit(self.session, actor, "report.upload", report.id)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            storage_path(key).unlink(missing_ok=True)
            raise
        return report

    async def withdraw(self, report_id: int, actor: UserRead) -> Report:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        report = await self.get_by_id(report_id)
        if report.final_status == "COMPLETE":
            require_role(actor, MANAGERS)
        await TestingWorkflow(self.session).get_test(report.knowledge_test_id, actor, write=True)
        report.electronic_status = "DRAFT"
        report.paper_status = "MISSING"
        report.final_status = "PENDING"
        audit(self.session, actor, "report.withdraw", report.id)
        await self.session.commit()
        return report

    async def review(
        self, report_id: int, version: str, approved: bool, comment: str | None, actor: UserRead
    ) -> Report:
        require_role(actor, MANAGERS | {UserRole.DEPARTMENT_HEAD})
        report = await self.get_by_id(report_id)
        test = await TestingWorkflow(self.session).get_test(report.knowledge_test_id, actor, write=True)
        from app.modules.periods.service import PeriodService

        period = await PeriodService(self.session).get_by_id(test.period_id)
        if version == "paper" and not period.paper_reports_required:
            raise ConflictError("Приём бумажных отчётов в этом семестре отключён ЛПР")
        if not approved and not (comment or "").strip():
            raise ValidationError("Укажите замечание при отклонении отчёта")
        if version == "electronic" and not report.electronic_file_key:
            raise ConflictError("Электронная версия не загружена")
        if version == "electronic" and approved and report.electronic_status == "REJECTED":
            raise ConflictError("Необходима повторная загрузка исправленного отчёта")
        if version == "paper" and report.electronic_status != "APPROVED":
            raise ConflictError("Сначала должна быть одобрена электронная версия")
        setattr(report, version + "_status", "APPROVED" if approved else "REJECTED")
        setattr(report, version + "_comment", None if approved else comment.strip())
        if version == "electronic" and not approved:
            report.paper_status = "MISSING"
        report.final_status = (
            "COMPLETE"
            if (
                report.electronic_status == "APPROVED"
                and (not period.paper_reports_required or report.paper_status == "APPROVED")
            )
            else "PENDING"
        )
        audit(self.session, actor, f"report.review.{version}", report.id)
        await self.session.commit()
        return report

    async def refresh_period_completion(self, period) -> None:
        """Recalculate completion without discarding earlier paper review decisions."""
        from app.modules.testing.models import KnowledgeTest

        reports = (
            await self.session.scalars(
                select(Report).join(KnowledgeTest).where(KnowledgeTest.period_id == period.id)
            )
        ).all()
        for report in reports:
            report.final_status = (
                "COMPLETE"
                if (
                    report.electronic_status == "APPROVED"
                    and (not period.paper_reports_required or report.paper_status == "APPROVED")
                )
                else "PENDING"
            )

    async def approve_electronic(self, report_id: int, actor: UserRead) -> Report:
        return await self.review(report_id, "electronic", True, None, actor)

    async def reject_electronic(self, report_id: int, comment: str, actor: UserRead) -> Report:
        return await self.review(report_id, "electronic", False, comment, actor)

    async def approve_paper(self, report_id: int, actor: UserRead) -> Report:
        return await self.review(report_id, "paper", True, None, actor)

    async def reject_paper(self, report_id: int, comment: str, actor: UserRead) -> Report:
        return await self.review(report_id, "paper", False, comment, actor)

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> ReportStatistics:
        from app.modules.departments.service import DepartmentService
        from app.modules.groups.models import StudyGroup
        from app.modules.testing.models import KnowledgeTest

        ids = await DepartmentService(self.session).subtree_ids(department_id)
        reports = (
            await self.session.scalars(
                select(Report)
                .join(KnowledgeTest, KnowledgeTest.id == Report.knowledge_test_id)
                .join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id)
                .where(KnowledgeTest.period_id == period_id, StudyGroup.department_id.in_(ids))
            )
        ).all()
        return ReportStatistics(
            electronic_submitted=sum(r.electronic_status == "APPROVED" for r in reports),
            electronic_with_issues=sum(r.electronic_status == "REJECTED" for r in reports),
            paper_submitted=sum(r.paper_status == "APPROVED" for r in reports),
            paper_with_issues=sum(r.paper_status == "REJECTED" for r in reports),
        )
