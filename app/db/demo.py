"""Opt-in development fixtures, committed atomically and never overwriting existing rows."""

import logging
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    DepartmentType,
    KnowledgeTestStatus,
    ParticipationStatus,
    TestingPeriodStatus,
    UserRole,
)
from app.modules.departments.models import Department
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.periods.models import TestingPeriod
from app.modules.reports.models import Report
from app.modules.results.models import TestResult
from app.modules.students.models import Student
from app.modules.testing.models import KnowledgeTest
from app.modules.users.models import User

logger = logging.getLogger(__name__)
MARKER = "demo:admin"


async def seed_demo_data(session: AsyncSession) -> bool:
    """A unique marker and one transaction make repeated starts safe."""
    marker = select(User.id).where(User.external_id == MARKER)
    try:
        async with session.begin():
            if await session.scalar(marker) is not None:
                logger.info("Demo data already initialized")
                return False
            await _insert_demo_data(session)
    except IntegrityError:
        # Another worker may have completed the same seed while we were starting.
        if await session.scalar(marker) is None:
            raise
        return False
    logger.info("Demo data initialized")
    return True


async def _insert_demo_data(session: AsyncSession) -> None:
    today = date.today()
    year = today.year if today.month >= 9 else today.year - 1
    semester = 1 if today.month >= 9 or today.month == 1 else 2
    current = (year, semester)

    users = [
        User(
            external_id=MARKER,
            full_name="Демо Администратор",
            email="admin@example.test",
            role=UserRole.ADMIN,
        ),
        User(
            external_id="demo:lpr",
            full_name="Демо Руководитель",
            email="lpr@example.test",
            role=UserRole.LPR,
        ),
        User(
            external_id="demo:teacher",
            full_name="Демо Преподаватель",
            email="teacher@example.test",
            role=UserRole.TEACHER,
        ),
        User(
            external_id="demo:guest", full_name="Демо Гость", role=UserRole.GUEST, is_active=False
        ),
    ]
    faculties = [
        Department(
            name="Демо: факультет информационных технологий",
            short_name="Демо ФИТ",
            type=DepartmentType.FACULTY,
        ),
        Department(
            name="Демо: факультет экономики и управления",
            short_name="Демо ФЭУ",
            type=DepartmentType.FACULTY,
        ),
        Department(
            name="Демо: инженерный институт", short_name="Демо ИИ", type=DepartmentType.INSTITUTE
        ),
    ]
    session.add_all([*users, *faculties])
    await session.flush()
    programs = [
        StudyProgram(
            name="Демо: информационные системы и технологии",
            code="09.03.02",
            faculty_id=faculties[0].id,
        ),
        StudyProgram(
            name="Демо: программная инженерия", code="09.03.04", faculty_id=faculties[0].id
        ),
        StudyProgram(name="Демо: экономика", code="38.03.01", faculty_id=faculties[1].id),
        StudyProgram(name="Демо: машиностроение", code="15.03.01", faculty_id=faculties[2].id),
    ]
    disciplines = [
        Discipline(
            external_id="demo:databases", name="Демо: базы данных", department_id=faculties[0].id
        ),
        Discipline(external_id="demo:math", name="Демо: математика", department_id=faculties[1].id),
        Discipline(
            external_id="demo:mechanics", name="Демо: механика", department_id=faculties[2].id
        ),
    ]
    periods = []
    for start_year in range(year - 1, year + 2):
        for part in (1, 2):
            key = (start_year, part)
            status = (
                TestingPeriodStatus.CLOSED
                if key < current
                else (TestingPeriodStatus.OPEN if key == current else TestingPeriodStatus.DRAFT)
            )
            periods.append(
                TestingPeriod(
                    name=f"Демо: {'Осень' if part == 1 else 'Весна'} {start_year if part == 1 else start_year + 1}",
                    academic_year=f"{start_year}/{start_year + 1}",
                    semester=part,
                    start_date=date(start_year, 9, 1) if part == 1 else date(start_year + 1, 2, 1),
                    end_date=date(start_year + 1, 1, 31)
                    if part == 1
                    else date(start_year + 1, 8, 31),
                    status=status,
                )
            )
    session.add_all([*programs, *disciplines, *periods])
    await session.flush()
    groups = []
    for index in range(6):
        program = programs[index % len(programs)]
        groups.append(
            StudyGroup(
                external_id=f"demo:group:{index}",
                name=f"Демо-{index + 1:03d}",
                admission_year=year - (index % 3),
                study_program_id=program.id,
                department_id=program.faculty_id,
            )
        )
    session.add_all(groups)
    await session.flush()
    students = []
    tests = []
    for index, group in enumerate(groups):
        students.append(
            Student(
                external_id=f"demo:student:{index}",
                full_name=f"Демо Студент {index + 1}",
                group_id=group.id,
            )
        )
        for period in periods:
            # A group without any assignments still appears when filtering its enrollment.
            if index == 5 and period.academic_year != f"{year}/{year + 1}":
                continue
            session.add(GroupPeriod(group_id=group.id, period_id=period.id))
            if index == 5 or (index + period.semester) % 4 == 0:
                continue
            status = {
                TestingPeriodStatus.CLOSED: KnowledgeTestStatus.COMPLETED,
                TestingPeriodStatus.OPEN: KnowledgeTestStatus.IN_PROGRESS,
                TestingPeriodStatus.DRAFT: KnowledgeTestStatus.PLANNED,
            }[period.status]
            if index == 3 and period.status == TestingPeriodStatus.CLOSED:
                status = KnowledgeTestStatus.CANCELLED
            test = KnowledgeTest(
                group_id=group.id,
                period_id=period.id,
                discipline_id=disciplines[index % len(disciplines)].id,
                teacher_id=users[2].id,
                status=status,
                scheduled_at=datetime.combine(
                    today if period.status == TestingPeriodStatus.OPEN else period.start_date,
                    time(10, 0),
                ),
            )
            tests.append((test, index))
            session.add(test)
    session.add_all(students)
    await session.flush()
    for test, index in tests:
        if test.status not in {KnowledgeTestStatus.COMPLETED, KnowledgeTestStatus.IN_PROGRESS}:
            continue
        completed = test.status == KnowledgeTestStatus.COMPLETED
        session.add(
            Report(
                knowledge_test_id=test.id,
                electronic_status="Принят" if completed else "На проверке",
                electronic_comment="Демонстрационный отчёт"
                if completed
                else "Демо: ожидается проверка",
                paper_status="Получен" if completed else "Не сдан",
                final_status="Принят" if completed else "В работе",
            )
        )
        if completed:
            session.add(
                TestResult(
                    knowledge_test_id=test.id,
                    student_id=students[index].id,
                    intermediate_result=75.0,
                    testing_result=80.0,
                    participation_status=ParticipationStatus.PASSED,
                )
            )
