from datetime import datetime

import pytest

from app.core.enums import UserRole
from app.modules.users.dependencies import get_current_user
from app.modules.users.models import AuditEvent, User
from app.modules.users.schemas import UserRead


@pytest.fixture
async def audit_context(db_session, application):
    admin = User(id=1, full_name="Администратор", role=UserRole.ADMIN)
    teacher = User(id=2, full_name="Преподаватель", role=UserRole.TEACHER)
    db_session.add_all([admin, teacher])
    await db_session.flush()
    db_session.add_all(
        [
            AuditEvent(
                id=1,
                actor_id=1,
                action="order.save",
                entity_id=10,
                details={},
                created_at=datetime(2026, 11, 1, 10, 0),
            ),
            AuditEvent(
                id=2,
                actor_id=1,
                action="period.delete",
                entity_id=20,
                details={},
                created_at=datetime(2026, 11, 2, 10, 0),
            ),
            AuditEvent(
                id=3,
                actor_id=2,
                action="user.save",
                entity_id=30,
                details={},
                created_at=datetime(2026, 11, 3, 10, 0),
            ),
        ]
    )
    await db_session.commit()

    context = {"actor": UserRead.model_validate(admin), "teacher": teacher}
    application.dependency_overrides[get_current_user] = lambda: context["actor"]
    yield context
    application.dependency_overrides.pop(get_current_user, None)


async def test_audit_returns_events_newest_first(client, audit_context):
    response = await client.get("/api/administration/audit")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [3, 2, 1]


async def test_audit_filters_by_action(client, audit_context):
    response = await client.get("/api/administration/audit?action=period.delete")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [2]


async def test_audit_filters_by_actor(client, audit_context):
    response = await client.get("/api/administration/audit?actor_id=2")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [3]


async def test_audit_filters_by_date_range(client, audit_context):
    response = await client.get("/api/administration/audit?date_from=2026-11-02&date_to=2026-11-03")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [3, 2]


async def test_audit_filters_until_one_day(client, audit_context):
    response = await client.get("/api/administration/audit?date_to=2026-11-01")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [1]


async def test_audit_rejects_reversed_date_range(client, audit_context):
    response = await client.get("/api/administration/audit?date_from=2026-11-03&date_to=2026-11-01")

    assert response.status_code == 422


async def test_audit_combines_filters(client, audit_context):
    response = await client.get(
        "/api/administration/audit?action=order.save&actor_id=1&date_from=2026-11-01"
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [1]


async def test_teacher_cannot_read_audit(client, audit_context):
    audit_context["actor"] = UserRead.model_validate(audit_context["teacher"])

    response = await client.get("/api/administration/audit")

    assert response.status_code == 403
