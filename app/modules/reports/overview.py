"""Scoped report list, including checks without an uploaded report."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DepartmentType, KnowledgeTestStatus, UserRole
from app.core.permissions import MANAGERS, PLANNERS, require_role
from app.modules.departments.service import DepartmentService
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup, StudyProgram
from app.modules.periods.models import TestingPeriod
from app.modules.reports.models import Report
from app.modules.reports.schemas import ReportOverview
from app.modules.results.service import ResultService
from app.modules.students.service import StudentService
from app.modules.testing.models import KnowledgeTest
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


class ReportOverviewService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_reports(
        self,
        actor: UserRead,
        *,
        period_id: int | None = None,
        faculty_id: int | None = None,
        department_id: int | None = None,
        discipline_id: int | None = None,
        electronic_status: str | None = None,
        paper_status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ReportOverview]:
        require_role(actor, PLANNERS | {UserRole.DEPARTMENT_HEAD, UserRole.TEACHER})
        departments = DepartmentService(self.session)
        query = (
            select(KnowledgeTest, Report, StudyGroup, Discipline, TestingPeriod, User, StudyProgram)
            .join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id)
            .join(Discipline, Discipline.id == KnowledgeTest.discipline_id)
            .join(TestingPeriod, TestingPeriod.id == KnowledgeTest.period_id)
            .outerjoin(Report, Report.knowledge_test_id == KnowledgeTest.id)
            .outerjoin(User, User.id == KnowledgeTest.teacher_id)
            .outerjoin(StudyProgram, StudyProgram.id == StudyGroup.study_program_id)
            .where(KnowledgeTest.status != KnowledgeTestStatus.CANCELLED)
        )

        def groups_in(ids: set[int]):
            return or_(
                StudyGroup.department_id.in_(ids),
                StudyGroup.department_id.is_(None) & StudyProgram.faculty_id.in_(ids),
            )

        if actor.role == UserRole.TEACHER:
            query = query.where(KnowledgeTest.teacher_id == actor.id)
        elif actor.role not in MANAGERS:
            ids = await departments.subtree_ids(actor.department_id)
            scope = groups_in(ids)
            if actor.role != UserRole.DEPARTMENT_HEAD:
                scope = scope | Discipline.department_id.in_(ids)
            query = query.where(scope)
        if faculty_id is not None:
            query = query.where(groups_in(await departments.subtree_ids(faculty_id)))
        if department_id is not None:
            query = query.where(Discipline.department_id == department_id)
        if discipline_id is not None:
            query = query.where(KnowledgeTest.discipline_id == discipline_id)
        if period_id is not None:
            query = query.where(KnowledgeTest.period_id == period_id)
        if electronic_status:
            query = query.where(
                func.coalesce(Report.electronic_status, "MISSING") == electronic_status
            )
        if paper_status:
            query = query.where(
                TestingPeriod.paper_reports_required.is_(True),
                func.coalesce(Report.paper_status, "MISSING") == paper_status,
            )
        records = (
            await self.session.execute(query.order_by(KnowledgeTest.id).offset(offset).limit(limit))
        ).all()
        totals = await StudentService(self.session).count_by_groups({row[2].id for row in records})
        participants = await ResultService(self.session).participation_counts(
            {row[0].id for row in records}
        )
        units = {unit.id: unit for unit in await departments.list_departments(limit=100000)}

        def faculty_of(group, program):
            current = units.get(group.department_id)
            visited = set()
            while current is not None and current.id not in visited:
                if current.type in {DepartmentType.FACULTY, DepartmentType.INSTITUTE}:
                    return current
                visited.add(current.id)
                current = units.get(current.parent_id)
            return units.get(program.faculty_id) if program else None

        rows = []
        for test, report, group, discipline, period, teacher, program in records:
            faculty = faculty_of(group, program)
            unit = units.get(discipline.department_id)
            total, participated = totals.get(group.id, 0), participants.get(test.id, 0)
            electronic = (report.electronic_status if report else None) or "MISSING"
            paper = (report.paper_status if report else None) or "MISSING"
            complete = electronic == "APPROVED" and (
                not period.paper_reports_required or paper == "APPROVED"
            )
            rows.append(
                ReportOverview(
                    knowledge_test_id=test.id,
                    report_id=report.id if report else None,
                    period_id=period.id,
                    period_name=period.name,
                    group_id=group.id,
                    group_name=group.name,
                    faculty_id=faculty.id if faculty else None,
                    faculty_name=faculty.name if faculty else None,
                    department_id=discipline.department_id,
                    department_name=unit.name if unit else None,
                    discipline_id=discipline.id,
                    discipline_name=discipline.name,
                    teacher_name=teacher.full_name if teacher else None,
                    previous_teacher_name=report.previous_teacher_name if report else None,
                    electronic_status=electronic,
                    electronic_comment=report.electronic_comment if report else None,
                    paper_status=paper if period.paper_reports_required else "NOT_REQUIRED",
                    paper_comment=report.paper_comment if report else None,
                    paper_reports_required=period.paper_reports_required,
                    final_status="COMPLETE" if complete else "PENDING",
                    has_file=bool(report and report.electronic_file_key),
                    total_students=total,
                    participated_students=participated,
                    participation_percentage=round(100 * participated / total, 2) if total else 0,
                    at_least_half_participated=total > 0 and 2 * participated >= total,
                )
            )
        return rows
