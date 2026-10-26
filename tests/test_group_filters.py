from datetime import date

import pytest

from app.core.enums import DepartmentType
from app.modules.departments.models import Department
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.periods.models import TestingPeriod as Period


@pytest.fixture
async def group_catalog(db_session, application):
    from app.core.enums import UserRole
    from app.modules.users.dependencies import get_current_user
    from app.modules.users.models import User
    from app.modules.users.schemas import UserRead

    user = User(id=1, full_name="Администратор", role=UserRole.ADMIN)
    db_session.add(user)
    await db_session.flush()
    application.dependency_overrides[get_current_user] = lambda: UserRead.model_validate(user)
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


async def test_testing_overview_is_scoped_and_includes_empty_groups(client, group_catalog):
    from app.core.enums import KnowledgeTestStatus
    from app.modules.disciplines.models import Discipline
    from app.modules.testing.models import KnowledgeTest

    group_catalog.add(Discipline(id=1, name="Базы данных"))
    await group_catalog.flush()
    group_catalog.add_all(
        [
            KnowledgeTest(
                id=1, group_id=1, period_id=1, discipline_id=1, status=KnowledgeTestStatus.COMPLETED
            ),
            KnowledgeTest(
                id=2,
                group_id=1,
                period_id=2,
                discipline_id=1,
                status=KnowledgeTestStatus.IN_PROGRESS,
            ),
            KnowledgeTest(id=3, group_id=1, period_id=3, discipline_id=1),
            KnowledgeTest(id=4, group_id=2, period_id=2, discipline_id=1),
        ]
    )
    await group_catalog.commit()
    response = await client.get("/api/groups/testing-overview?faculty_id=1")
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [1, 3]
    assert rows[1]["testings"] == []
    assert [test["status"] for test in rows[0]["testings"]] == [
        "COMPLETED",
        "IN_PROGRESS",
        "PLANNED",
    ]
    assert rows[0]["testings"][0]["discipline_name"] == "Базы данных"
    assert (await client.get("/api/groups/testing-overview?offset=1&limit=1")).json()[0]["id"] == 2
    assert (await client.get("/api/groups/testing-overview?faculty_id=999")).json() == []


async def test_create_testing_enrolls_group_and_requires_planned_status(client, group_catalog):
    from datetime import timedelta

    from app.core.enums import TestingPeriodStatus
    from app.modules.disciplines.models import Discipline

    period = await group_catalog.get(Period, 2)
    period.start_date = date.today() - timedelta(days=1)
    period.end_date = date.today() + timedelta(days=30)
    period.status = TestingPeriodStatus.OPEN

    group_catalog.add(Discipline(id=1, name="Базы данных"))
    await group_catalog.commit()
    payload = {"group_id": 3, "period_id": 2, "discipline_id": 1, "status": "PLANNED"}
    response = await client.post("/api/testing", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "PLANNED"
    assert (
        await client.post("/api/testing", json={**payload, "status": "COMPLETED"})
    ).status_code == 422
    await client.post("/api/testing", json=payload)
    groups = (await client.get("/api/groups?academic_year=2025/2026&semester=2")).json()
    assert [row["id"] for row in groups] == [1, 2, 3]
    response = await client.post("/api/testing", json={**payload, "group_id": 999})
    assert response.status_code == 404


async def test_invalid_testing_status_is_rejected(client, group_catalog):
    response = await client.post(
        "/api/testing",
        json={
            "group_id": 1,
            "period_id": 1,
            "discipline_id": 1,
            "status": "WRONG",
        },
    )
    assert response.status_code == 422
