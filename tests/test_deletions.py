from datetime import date

import pytest
from sqlalchemy import select

from app.core.enums import TestingPeriodStatus as PeriodStatus
from app.core.enums import UserRole
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup
from app.modules.periods.models import TestingPeriod as Period
from app.modules.testing.models import KnowledgeTest
from app.modules.users.dependencies import get_current_user
from app.modules.users.models import AuditEvent, User
from app.modules.users.schemas import UserRead


@pytest.fixture
async def deletion_context(db_session, application):
    admin = User(id=1, full_name="Администратор", role=UserRole.ADMIN)
    teacher = User(id=2, full_name="Преподаватель", role=UserRole.TEACHER)
    db_session.add_all([admin, teacher])
    db_session.add_all(
        [
            Period(
                id=1,
                name="Пустой период",
                academic_year="2026/2027",
                semester=1,
                start_date=date(2026, 9, 1),
                end_date=date(2027, 1, 31),
                status=PeriodStatus.DRAFT,
            ),
            Period(
                id=2,
                name="Период с тестированием",
                academic_year="2026/2027",
                semester=2,
                start_date=date(2027, 2, 1),
                end_date=date(2027, 6, 30),
                status=PeriodStatus.DRAFT,
            ),
            Period(
                id=3,
                name="Период с зачислением группы",
                academic_year="2027/2028",
                semester=1,
                start_date=date(2027, 9, 1),
                end_date=date(2028, 1, 31),
                status=PeriodStatus.DRAFT,
            ),
            Discipline(id=1, name="Свободная дисциплина"),
            Discipline(id=2, name="Занятая дисциплина"),
            StudyGroup(id=1, name="261-001"),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            KnowledgeTest(id=1, period_id=2, group_id=1, discipline_id=2),
            GroupPeriod(group_id=1, period_id=3),
        ]
    )
    await db_session.commit()

    context = {
        "actor": UserRead.model_validate(admin),
        "admin": admin,
        "teacher": teacher,
    }
    application.dependency_overrides[get_current_user] = lambda: context["actor"]
    yield context
    application.dependency_overrides.pop(get_current_user, None)


async def test_delete_empty_period(client, db_session, deletion_context):
    response = await client.delete("/api/periods/1")

    assert response.status_code == 204
    assert await db_session.get(Period, 1) is None
    event = await db_session.scalar(select(AuditEvent).where(AuditEvent.action == "period.delete"))
    assert event is not None
    assert event.entity_id == 1


async def test_delete_period_with_links_returns_conflict(client, db_session, deletion_context):
    response = await client.delete("/api/periods/2")

    assert response.status_code == 409
    assert "тестирования" in response.json()["detail"]
    assert await db_session.get(Period, 2) is not None


async def test_delete_period_with_group_enrollment_returns_conflict(
    client, db_session, deletion_context
):
    response = await client.delete("/api/periods/3")

    assert response.status_code == 409
    assert "группы периода" in response.json()["detail"]
    assert await db_session.get(Period, 3) is not None


async def test_delete_unknown_period_returns_not_found(client, deletion_context):
    response = await client.delete("/api/periods/999")

    assert response.status_code == 404


async def test_teacher_cannot_delete_period(client, deletion_context):
    deletion_context["actor"] = UserRead.model_validate(deletion_context["teacher"])

    response = await client.delete("/api/periods/1")

    assert response.status_code == 403


async def test_delete_unused_discipline(client, db_session, deletion_context):
    response = await client.delete("/api/disciplines/1")

    assert response.status_code == 204
    assert await db_session.get(Discipline, 1) is None
    event = await db_session.scalar(
        select(AuditEvent).where(AuditEvent.action == "discipline.delete")
    )
    assert event is not None
    assert event.entity_id == 1


async def test_delete_discipline_used_by_test_returns_conflict(
    client, db_session, deletion_context
):
    response = await client.delete("/api/disciplines/2")

    assert response.status_code == 409
    assert "тестированиях" in response.json()["detail"]
    assert await db_session.get(Discipline, 2) is not None


async def test_delete_unknown_discipline_returns_not_found(client, deletion_context):
    response = await client.delete("/api/disciplines/999")

    assert response.status_code == 404


async def test_teacher_cannot_delete_discipline(client, deletion_context):
    deletion_context["actor"] = UserRead.model_validate(deletion_context["teacher"])

    response = await client.delete("/api/disciplines/1")

    assert response.status_code == 403


async def test_delete_routes_are_exposed_in_openapi(client):
    paths = (await client.get("/openapi.json")).json()["paths"]

    assert "delete" in paths["/api/periods/{period_id}"]
    assert "delete" in paths["/api/disciplines/{discipline_id}"]
