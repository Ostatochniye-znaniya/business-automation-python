import csv
import io
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.core.enums import DepartmentType, UserRole
from app.core.enums import TestingPeriodStatus as PeriodStatus
from app.modules.departments.models import Department
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.groups.recommendation_models import GroupRecommendation, RecommendationHistory
from app.modules.periods.models import TestingPeriod as Period
from app.modules.users.models import User


@pytest.fixture
async def recommendations_catalog(db_session, application):
    today = date.today()
    db_session.add(Department(id=1, name="Факультет", type=DepartmentType.FACULTY))
    db_session.add_all(
        [
            User(id=1, full_name="Администратор", role=UserRole.ADMIN),
            User(id=2, full_name="ЛПР", role=UserRole.LPR),
            User(id=3, full_name="Преподаватель", role=UserRole.TEACHER),
            User(id=4, full_name="Отключённый ЛПР", role=UserRole.LPR, is_active=False),
        ]
    )
    await db_session.flush()
    db_session.add(StudyProgram(id=1, name="Направление", faculty_id=1))
    for identifier, status, start, end in [
        (1, PeriodStatus.OPEN, today - timedelta(days=10), today + timedelta(days=30)),
        (2, PeriodStatus.DRAFT, today + timedelta(days=60), today + timedelta(days=90)),
        (3, PeriodStatus.CLOSED, today - timedelta(days=10), today + timedelta(days=30)),
        (4, PeriodStatus.OPEN, today - timedelta(days=30), today - timedelta(days=1)),
    ]:
        db_session.add(
            Period(
                id=identifier,
                name=f"Период {identifier}",
                academic_year=f"{today.year}/{today.year + 1}",
                semester=1,
                start_date=start,
                end_date=end,
                status=status,
            )
        )
    await db_session.flush()
    db_session.add_all(
        [
            StudyGroup(id=i, name=f"Группа {i}", study_program_id=1, admission_year=today.year - 1)
            for i in range(1, 4)
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            GroupPeriod(group_id=group, period_id=period)
            for group in (1, 2)
            for period in (1, 2, 3, 4)
        ]
    )
    await db_session.commit()
    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, APP_ENV="test", DEV_USER_ID=2
    )
    return db_session


def change(group=1, period=1, recommended=True, version=0):
    return {
        "group_id": group,
        "period_id": period,
        "recommended": recommended,
        "expected_version": version,
    }


async def save(client, *changes):
    return await client.put("/api/recommendations", json={"changes": changes})


async def test_save_remove_restore_and_author_history(client, recommendations_catalog):
    response = await save(client, change())
    assert response.status_code == 200
    record = response.json()[0]
    assert record["version"] == 1 and record["changed_by_id"] == 2
    assert record["changed_by_name"] == "ЛПР"
    assert record["changed_at"].endswith("Z")
    assert len((await client.get("/api/recommendations?period_id=1")).json()) == 1
    overview = (await client.get("/api/groups/testing-overview")).json()[0]
    assert overview["recommendations"][0]["recommended"] is True
    assert 1 in overview["enrolled_period_ids"]
    # An unchanged save does not create another history event.
    assert (await save(client, change(version=1))).json()[0]["version"] == 1
    assert (await save(client, change(recommended=False, version=1))).status_code == 200
    assert (await client.get("/api/recommendations?period_id=1")).json() == []
    assert (await save(client, change(version=2))).json()[0]["version"] == 3
    history = (await client.get("/api/recommendations/history?group_id=1")).json()
    assert [event["recommended"] for event in history] == [True, False, True]
    assert [event["version"] for event in history] == [3, 2, 1]
    assert all(event["changed_by_id"] == 2 for event in history)


async def test_batch_preserves_other_groups_and_periods(client, recommendations_catalog):
    assert (await save(client, change(), change(group=2), change(period=2))).status_code == 200
    assert (await save(client, change(recommended=False, version=1))).status_code == 200
    assert [
        record["group_id"]
        for record in (await client.get("/api/recommendations?period_id=1")).json()
    ] == [2]
    assert len((await client.get("/api/recommendations?period_id=2")).json()) == 1
    assert len((await client.get("/api/recommendations?limit=1&offset=1")).json()) == 1
    assert (await client.get("/api/recommendations/history?group_id=999")).status_code == 404


async def test_stale_version_returns_conflict_without_overwriting(client, recommendations_catalog):
    await save(client, change())
    response = await save(client, change(recommended=False))
    assert response.status_code == 409
    assert (await client.get("/api/recommendations")).json()[0]["recommended"] is True
    assert (
        await recommendations_catalog.scalar(
            select(func.count()).select_from(RecommendationHistory)
        )
        == 1
    )


async def test_invalid_batch_is_rolled_back_as_a_whole(client, recommendations_catalog):
    response = await save(client, change(), change(group=3))
    assert response.status_code == 422
    assert (
        await recommendations_catalog.scalar(select(func.count()).select_from(GroupRecommendation))
        == 0
    )
    assert (
        await recommendations_catalog.scalar(
            select(func.count()).select_from(RecommendationHistory)
        )
        == 0
    )


@pytest.mark.parametrize("period", [3, 4])
async def test_closed_and_expired_periods_are_read_only(client, recommendations_catalog, period):
    assert (await save(client, change(period=period))).status_code == 409
    assert (await client.get("/api/recommendations")).json() == []


@pytest.mark.parametrize("user, expected", [(1, 200), (2, 200), (3, 403), (4, 403)])
async def test_write_permissions(client, application, recommendations_catalog, user, expected):
    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, APP_ENV="test", DEV_USER_ID=user
    )
    assert (await save(client, change())).status_code == expected


async def test_missing_identity_cannot_write_or_impersonate_by_header(
    client, application, recommendations_catalog
):
    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, APP_ENV="test"
    )
    assert (await save(client, change())).status_code == 403
    assert (
        await client.put(
            "/api/recommendations", json={"changes": [change()]}, headers={"X-User-Id": "2"}
        )
    ).status_code == 403
    assert (await client.get("/api/users/me")).status_code == 403


async def test_current_user_is_taken_from_database(client, recommendations_catalog):
    response = await client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["id"] == 2
    assert response.json()["role"] == "LPR"


async def test_export_uses_saved_selection_and_escapes_spreadsheet_formulas(
    client, recommendations_catalog
):
    session = recommendations_catalog
    group = await session.get(StudyGroup, 1)
    group.name = "=FORMULA()"
    await session.commit()
    await save(client, change())
    await save(client, change(group=2, period=2))
    response = await client.get("/api/recommendations/export?period_id=1&faculty_id=1")
    assert response.status_code == 200
    assert response.text.startswith("\ufeff")
    assert (
        'attachment; filename="recommended-groups-1.csv"' == response.headers["content-disposition"]
    )
    rows = list(csv.reader(io.StringIO(response.text.lstrip("\ufeff")), delimiter=";"))
    assert len(rows) == 2
    assert rows[1][0] == "'=FORMULA()"
    assert rows[1][6] == "ЛПР"
    assert (await client.get("/api/recommendations/export?period_id=999")).status_code == 404
    empty = await client.get("/api/recommendations/export?period_id=1&study_program_id=999")
    assert len(list(csv.reader(io.StringIO(empty.text), delimiter=";"))) == 1


@pytest.mark.parametrize(
    "changes",
    [
        [],
        [change(), change()],
        [{**change(), "expected_version": -1}],
        [{**change(), "changed_by_id": 1}],
    ],
)
async def test_invalid_save_payload_is_rejected(client, recommendations_catalog, changes):
    assert (await client.put("/api/recommendations", json={"changes": changes})).status_code == 422


def test_production_cannot_use_development_identity():
    with pytest.raises(ValueError, match="DEV_USER_ID"):
        Settings(_env_file=None, APP_ENV="production", DEV_USER_ID=2)


async def test_removing_recommendation_preserves_testing_and_report(
    client, recommendations_catalog
):
    from app.modules.disciplines.models import Discipline
    from app.modules.reports.models import Report
    from app.modules.testing.models import KnowledgeTest

    session = recommendations_catalog
    session.add(Discipline(id=1, name="Базы данных"))
    await session.flush()
    session.add(KnowledgeTest(id=1, group_id=1, period_id=1, discipline_id=1))
    await session.flush()
    session.add(Report(id=1, knowledge_test_id=1, final_status="Принят"))
    await session.commit()
    await save(client, change())
    assert (await save(client, change(recommended=False, version=1))).status_code == 200
    assert await session.get(KnowledgeTest, 1) is not None
    assert (await session.get(Report, 1)).final_status == "Принят"
