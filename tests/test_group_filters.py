from datetime import date

import pytest

from app.core.enums import DepartmentType
from app.modules.departments.models import Department
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.periods.models import TestingPeriod as Period


@pytest.fixture
async def group_catalog(db_session):
    db_session.add_all(
        [
            Department(id=1, name="ФИТ", type=DepartmentType.FACULTY),
            Department(id=2, name="Институт", type=DepartmentType.INSTITUTE),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            StudyProgram(id=1, name="Информатика", faculty_id=1),
            StudyProgram(id=2, name="Экономика", faculty_id=2),
            Period(
                id=1,
                name="Осень",
                academic_year="2025/2026",
                semester=1,
                start_date=date(2025, 9, 1),
                end_date=date(2026, 1, 31),
            ),
            Period(
                id=2,
                name="Весна",
                academic_year="2025/2026",
                semester=2,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 8, 31),
            ),
            Period(
                id=3,
                name="Осень",
                academic_year="2026/2027",
                semester=1,
                start_date=date(2026, 9, 1),
                end_date=date(2027, 1, 31),
            ),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            StudyGroup(id=1, name="241-001", study_program_id=1),
            StudyGroup(id=2, name="241-002", study_program_id=2),
            StudyGroup(id=3, name="241-003", study_program_id=1),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            GroupPeriod(group_id=1, period_id=1),
            GroupPeriod(group_id=1, period_id=2),
            GroupPeriod(group_id=2, period_id=2),
            GroupPeriod(group_id=3, period_id=3),
        ]
    )
    await db_session.commit()
    return db_session


@pytest.mark.parametrize(
    "query, expected",
    [
        ("", [1, 2, 3]),
        ("faculty_id=1", [1, 3]),
        ("study_program_id=2", [2]),
        ("academic_year=2025/2026", [1, 2]),
        ("semester=2", [1, 2]),
        ("academic_year=2026/2027&semester=1&faculty_id=1&study_program_id=1", [3]),
        ("faculty_id=1&study_program_id=2", []),
        ("academic_year=2026/2027&semester=2", []),
        ("offset=1&limit=1", [2]),
    ],
)
async def test_group_filters_use_enrollment_without_requiring_tests(
    client, group_catalog, query, expected
):
    response = await client.get(f"/api/groups?{query}")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == expected


async def test_programs_are_scoped_to_faculty(client, group_catalog):
    response = await client.get("/api/programs?faculty_id=1")
    assert response.status_code == 200
    assert [program["id"] for program in response.json()] == [1]


@pytest.mark.parametrize("query", ["semester=3", "faculty_id=-1", "academic_year=wrong"])
async def test_invalid_group_filters(client, query):
    assert (await client.get(f"/api/groups?{query}")).status_code == 422
