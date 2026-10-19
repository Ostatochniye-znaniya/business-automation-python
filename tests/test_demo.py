from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

import app.main as main
from app.core.config import Settings
from app.db.base import Base
from app.db.demo import MARKER, seed_demo_data
from app.modules.groups.models import GroupPeriod, StudyGroup
from app.modules.testing.models import KnowledgeTest
from app.modules.users.models import User


async def counts(session):
    return {
        table.name: await session.scalar(select(func.count()).select_from(table))
        for table in Base.metadata.sorted_tables
    }


async def test_demo_seed_is_idempotent_and_preserves_existing_data(db_session):
    existing = User(external_id="university:1", full_name="Existing User")
    db_session.add(existing)
    await db_session.commit()
    assert await seed_demo_data(db_session) is True
    first = await counts(db_session)
    workflow_tables = {
        "orders",
        "access_requests",
        "audit_events",
        "import_logs",
        "dev_sessions",
        "group_participation",
    }
    assert all(value for name, value in first.items() if name not in workflow_tables)
    assert all(first[name] == 0 for name in workflow_tables)
    assert first["study_groups"] == 6
    assert first["testing_periods"] == 6
    assert first["study_programs"] == 4
    assert (
        await db_session.scalar(select(User.full_name).where(User.id == existing.id))
        == "Existing User"
    )
    await db_session.commit()
    assert await seed_demo_data(db_session) is False
    assert await counts(db_session) == first


async def test_seed_rolls_back_completely_on_failure(db_session, monkeypatch):
    async def failing_insert(session):
        session.add(User(external_id=MARKER, full_name="Incomplete seed"))
        await session.flush()
        raise RuntimeError("Seed failed")

    monkeypatch.setattr("app.db.demo._insert_demo_data", failing_insert)
    with pytest.raises(RuntimeError, match="Seed failed"):
        await seed_demo_data(db_session)
    assert await db_session.scalar(select(User.id).where(User.external_id == MARKER)) is None


@pytest.mark.parametrize("today", [date(2026, 1, 15), date(2026, 2, 15), date(2026, 9, 15)])
async def test_demo_includes_current_previous_and_future_periods(
    db_session, client, monkeypatch, today
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr("app.db.demo.date", FixedDate)
    await seed_demo_data(db_session)
    periods = (await client.get("/api/periods")).json()
    assert {period["status"] for period in periods} == {"CLOSED", "OPEN", "DRAFT"}
    current = next(period for period in periods if period["status"] == "OPEN")
    assert (
        date.fromisoformat(current["start_date"])
        <= today
        <= date.fromisoformat(current["end_date"])
    )
    query = f"academic_year={current['academic_year']}&semester={current['semester']}"
    groups = (await client.get(f"/api/groups/testing-overview?{query}")).json()
    assert len(groups) == 6
    assert any(not group["testings"] for group in groups)
    assert {test["status"] for group in groups for test in group["testings"]} == {
        "COMPLETED",
        "IN_PROGRESS",
        "PLANNED",
        "CANCELLED",
    }
    for test in (await db_session.scalars(select(KnowledgeTest))).all():
        assert await db_session.get(GroupPeriod, (test.group_id, test.period_id)) is not None
    faculties = (await client.get("/api/departments")).json()
    faculty_groups = (await client.get(f"/api/groups?faculty_id={faculties[0]['id']}")).json()
    assert 0 < len(faculty_groups) < len(groups)
    assert (await db_session.scalars(select(StudyGroup))).all()


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_demo_is_restricted_to_development_and_test(environment):
    with pytest.raises(ValueError, match="DEMO_DATA"):
        Settings(_env_file=None, APP_ENV=environment, DEMO_DATA=True)


@pytest.mark.parametrize("enabled", [False, True])
async def test_startup_respects_demo_flag_and_disposes_engine(application, monkeypatch, enabled):
    seed = AsyncMock()
    dispose = AsyncMock()
    session = object()

    @asynccontextmanager
    async def factory():
        yield session

    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(DEMO_DATA=enabled))
    monkeypatch.setattr(main, "session_factory", factory)
    monkeypatch.setattr(main, "seed_demo_data", seed)
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=dispose))
    async with main.lifespan(application):
        pass
    if enabled:
        seed.assert_awaited_once_with(session)
    else:
        seed.assert_not_awaited()
    dispose.assert_awaited_once()


async def test_existing_demo_database_gets_recommendations_without_resetting_user_choices(
    db_session, monkeypatch
):
    from app.db import demo
    from app.modules.groups.recommendation_models import GroupRecommendation

    initialize = demo._seed_demo_recommendations
    monkeypatch.setattr(demo, "_seed_demo_recommendations", AsyncMock())
    await seed_demo_data(db_session)
    monkeypatch.setattr(demo, "_seed_demo_recommendations", initialize)
    assert await seed_demo_data(db_session) is False
    record = await db_session.scalar(select(GroupRecommendation).limit(1))
    assert record is not None
    identifier = record.id
    record.recommended = False
    await db_session.commit()
    assert await seed_demo_data(db_session) is False
    assert (await db_session.get(GroupRecommendation, identifier)).recommended is False
