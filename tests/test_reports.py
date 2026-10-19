from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup
from app.modules.periods.models import TestingPeriod as Period
from app.modules.testing.models import KnowledgeTest


async def seed_knowledge_test(session: AsyncSession) -> int:
    period = Period(
        name="2025/2026, весенний семестр",
        academic_year="2025/2026",
        semester=1,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 6, 30),
    )
    group = StudyGroup(name="221-111")
    discipline = Discipline(name="Математика")
    session.add_all([period, group, discipline])
    await session.commit()
    await session.refresh(period)
    await session.refresh(group)
    await session.refresh(discipline)

    knowledge_test = KnowledgeTest(
        period_id=period.id,
        group_id=group.id,
        discipline_id=discipline.id,
    )
    session.add(knowledge_test)
    await session.commit()
    await session.refresh(knowledge_test)
    return knowledge_test.id


async def test_create_report(client, db_session):
    knowledge_test_id = await seed_knowledge_test(db_session)

    response = await client.post(
        "/api/reports",
        json={
            "knowledge_test_id": knowledge_test_id,
            "electronic_status": "SUBMITTED",
            "electronic_comment": "Файл загружен",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] > 0
    assert payload["knowledge_test_id"] == knowledge_test_id
    assert payload["electronic_status"] == "SUBMITTED"
    assert payload["paper_status"] is None


async def test_create_report_requires_existing_knowledge_test(client, db_session):
    response = await client.post("/api/reports", json={"knowledge_test_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "KnowledgeTest not found"


async def test_create_duplicate_report_returns_conflict(client, db_session):
    knowledge_test_id = await seed_knowledge_test(db_session)

    first = await client.post("/api/reports", json={"knowledge_test_id": knowledge_test_id})
    second = await client.post("/api/reports", json={"knowledge_test_id": knowledge_test_id})

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


async def test_update_report_changes_only_sent_fields(client, db_session):
    knowledge_test_id = await seed_knowledge_test(db_session)
    created = await client.post(
        "/api/reports",
        json={
            "knowledge_test_id": knowledge_test_id,
            "electronic_status": "SUBMITTED",
            "paper_status": "SUBMITTED",
        },
    )
    report_id = created.json()["id"]

    response = await client.put(
        f"/api/reports/{report_id}",
        json={"electronic_status": "ACCEPTED", "electronic_comment": "Без замечаний"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["electronic_status"] == "ACCEPTED"
    assert payload["electronic_comment"] == "Без замечаний"
    assert payload["paper_status"] == "SUBMITTED"


async def test_update_unknown_report_returns_not_found(client, db_session):
    response = await client.put("/api/reports/9999", json={"final_status": "ALL_DONE"})

    assert response.status_code == 404


async def test_delete_report(client, db_session):
    knowledge_test_id = await seed_knowledge_test(db_session)
    created = await client.post("/api/reports", json={"knowledge_test_id": knowledge_test_id})
    report_id = created.json()["id"]

    response = await client.delete(f"/api/reports/{report_id}")

    assert response.status_code == 204
    assert (await client.get(f"/api/reports/{report_id}")).status_code == 404
    listed = await client.get(f"/api/reports?knowledge_test_id={knowledge_test_id}")
    assert listed.status_code == 200
    assert listed.json() == []


async def test_delete_unknown_report_returns_not_found(client, db_session):
    response = await client.delete("/api/reports/9999")

    assert response.status_code == 404


async def test_create_report_validates_knowledge_test_id(client):
    response = await client.post("/api/reports", json={"knowledge_test_id": 0})

    assert response.status_code == 422
