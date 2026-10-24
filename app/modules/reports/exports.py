from datetime import UTC

from app.core.enums import KnowledgeTestStatus
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.time import MOSCOW
from app.modules.departments.service import DepartmentService
from app.modules.disciplines.service import DisciplineService
from app.modules.groups.service import GroupService
from app.modules.periods.service import PeriodService
from app.modules.results.service import ResultService
from app.modules.students.service import StudentService
from app.modules.testing.service import TestingService
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.service import UserService


class ExportService:
    def __init__(self, session):
        self.session = session

    async def summary(self, period_id, actor):
        from app.core.permissions import MANAGERS, require_role
        from app.modules.reports.documents import csv_bytes
        from app.modules.reports.service import ReportService

        require_role(actor, MANAGERS)
        await PeriodService(self.session).get_by_id(period_id)
        rows = []
        offset = 0
        while tests := await TestingService(self.session).list_by_period(period_id, offset, 100):
            for test in tests:
                if test.status == KnowledgeTestStatus.CANCELLED:
                    continue
                context = await self.context(test)
                results = await ResultService(self.session).get_by_test(test.id, limit=100000)
                reports = await ReportService(self.session).get_by_test(test.id)
                report = reports[0] if reports else None
                total_students = (
                    await StudentService(self.session).count_by_groups({test.group_id})
                ).get(test.group_id, 0)
                participated = sum(r.participation_status == "PASSED" for r in results)
                period = await PeriodService(self.session).get_by_id(period_id)
                rows.append(
                    [
                        context["group"],
                        context["program"],
                        context["discipline"],
                        context["teacher"],
                        test.status,
                        len(results),
                        sum(r.participation_status == "PASSED" for r in results),
                        sum(r.participation_status == "ABSENT" for r in results),
                        sum(r.participation_status == "NOT_ADMITTED" for r in results),
                        report.electronic_status if report else "MISSING",
                        (report.paper_status if report else "MISSING")
                        if period.paper_reports_required
                        else "NOT_REQUIRED",
                        total_students,
                        round(100 * participated / total_students, 2) if total_students else 0,
                        total_students > 0 and 2 * participated >= total_students,
                    ]
                )
            offset += len(tests)
        return csv_bytes(
            [
                "Группа",
                "Профиль",
                "Дисциплина",
                "Преподаватель",
                "Статус",
                "Записей результатов",
                "Прошли тестирование",
                "Не явились",
                "Не допущены",
                "Электронный отчёт",
                "Бумажный отчёт",
                "Всего студентов в группе",
                "Участие, %",
                "Участвовали не менее 50%",
            ],
            rows,
        )

    async def context(self, test):
        group = await GroupService(self.session).get_by_id(test.group_id)
        discipline = await DisciplineService(self.session).get_by_id(test.discipline_id)
        period = await PeriodService(self.session).get_by_id(test.period_id)
        program = (
            await GroupService(self.session).get_program(group.study_program_id)
            if group.study_program_id
            else None
        )
        teacher = (
            await UserService(self.session).get_by_id(test.teacher_id) if test.teacher_id else None
        )
        department = (
            await DepartmentService(self.session).get_by_id(discipline.department_id)
            if discipline.department_id
            else None
        )
        from app.core.enums import UserRole
        from app.modules.reports.service import ReportService

        reports = await ReportService(self.session).get_by_test(test.id)
        # The report belongs to the group's faculty, even for a cross-faculty discipline.
        faculty = (
            await DepartmentService(self.session).get_by_id(
                group.department_id or program.faculty_id
            )
            if group.department_id or program
            else None
        )
        visited = set()
        while faculty and faculty.type not in {"FACULTY", "INSTITUTE"}:
            if not faculty.parent_id or faculty.id in visited:
                faculty = None
                break
            visited.add(faculty.id)
            faculty = await DepartmentService(self.session).get_by_id(faculty.parent_id)
        faculty_id = faculty.id if faculty else None
        return {
            "group": group.name,
            "discipline": discipline.name,
            "academic_year": period.academic_year,
            "program": f"{program.code or ''} {program.name}".strip() if program else None,
            "program_code": program.code or "" if program else "",
            "program_name": program.name if program else "",
            "faculty": faculty.name if faculty else "",
            "teacher": teacher.full_name if teacher else "",
            "department": department.name if department else "",
            "previous_teacher": reports[0].previous_teacher_name if reports else None,
            "chair_head": await UserService(self.session).head_name(
                discipline.department_id, UserRole.CHAIR_HEAD
            ),
            "faculty_head": await UserService(self.session).head_name(
                faculty_id, UserRole.DEPARTMENT_HEAD
            ),
        }

    async def report(self, test_id, actor, *, template=False, pdf=False):
        test = await TestingWorkflow(self.session).get_test(test_id, actor)
        if not template and test.status != KnowledgeTestStatus.COMPLETED:
            raise ValidationError("Печатный отчёт доступен после заполнения результатов")
        context = await self.context(test)
        results = await ResultService(self.session).get_by_test(test_id, limit=100000)
        rows = []
        for result in results:
            student = await StudentService(self.session).get_by_id(result.student_id)
            rows.append(
                {
                    "student": student.full_name,
                    "intermediate_result": result.intermediate_result,
                    "testing_result": result.testing_result,
                    "participation_status": result.participation_status,
                }
            )
        rows.sort(key=lambda row: row["student"])
        if template:
            students = await StudentService(self.session).list_students(test.group_id, limit=100000)
            rows = [{"student": student.full_name} for student in students]
            rows.sort(key=lambda row: row["student"])
        from starlette.concurrency import run_in_threadpool

        from app.modules.reports.documents import report_docx, report_pdf

        return await run_in_threadpool(report_pdf if pdf else report_docx, context, rows, template)

    async def schedule(self, period_id, actor, department_id=None, signatory=""):
        from app.core.enums import UserRole
        from app.core.permissions import PLANNERS, require_role

        require_role(actor, PLANNERS | {UserRole.DEPARTMENT_HEAD, UserRole.TEACHER})
        period = await PeriodService(self.session).get_by_id(period_id)
        rows = []
        offset = 0
        while tests := await TestingService(self.session).list_by_period(period_id, offset, 100):
            for test in tests:
                if (
                    test.status == KnowledgeTestStatus.CANCELLED
                    or test.agreement_status != "AGREED"
                ):
                    continue
                try:
                    await TestingWorkflow(self.session).get_test(test.id, actor)
                except ForbiddenError:
                    continue
                if department_id:
                    group = await GroupService(self.session).get_by_id(test.group_id)
                    if group.department_id not in await DepartmentService(self.session).subtree_ids(
                        department_id
                    ):
                        continue
                context = await self.context(test)
                rows.append(
                    [
                        str(len(rows) + 1),
                        context["group"],
                        str(context["program"] or ""),
                        context["discipline"],
                        context["department"],
                        context["teacher"],
                        test.scheduled_at.replace(tzinfo=UTC)
                        .astimezone(MOSCOW)
                        .strftime("%d.%m.%Y %H:%M")
                        if test.scheduled_at
                        else "",
                        test.room or "",
                    ]
                )
            offset += len(tests)
        rows.sort(key=lambda row: (row[1], row[6]))
        for index, row in enumerate(rows, 1):
            row[0] = str(index)
        from starlette.concurrency import run_in_threadpool

        from app.modules.reports.documents import schedule_pdf

        return await run_in_threadpool(
            schedule_pdf,
            f"График проверки остаточных знаний. {period.name}",
            rows,
            signatory or "Декан / Директор __________________ / __________________",
        )
