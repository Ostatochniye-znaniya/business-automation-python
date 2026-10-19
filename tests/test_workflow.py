import io
from datetime import date, timedelta
from zipfile import ZipFile

import pytest

from app.core.config import get_settings
from app.core.enums import DepartmentType, UserRole
from app.core.enums import TestingPeriodStatus as PeriodStatus
from app.modules.departments.models import Department
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup
from app.modules.groups.recommendation_models import GroupRecommendation
from app.modules.periods.models import TestingPeriod as Period
from app.modules.students.models import Student
from app.modules.users.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


@pytest.fixture
async def workflow(db_session, application, tmp_path, monkeypatch):
    today = date.today()
    monkeypatch.setenv("REPORT_STORAGE_DIR", str(tmp_path / "reports"))
    get_settings.cache_clear()
    db_session.add(Department(id=1, name="Факультет", type=DepartmentType.FACULTY))
    await db_session.flush()
    db_session.add(Department(id=2, name="Кафедра", parent_id=1, type=DepartmentType.DEPARTMENT))
    await db_session.flush()
    users = [
        User(id=1, full_name="Администратор", role=UserRole.ADMIN),
        User(id=2, full_name="Заведующий", role=UserRole.CHAIR_HEAD, department_id=2),
        User(id=3, full_name="Преподаватель", role=UserRole.TEACHER, department_id=2),
        User(id=4, full_name="Гость", role=UserRole.GUEST),
    ]
    db_session.add_all(users)
    db_session.add(
        Period(
            id=1,
            name="Текущий",
            academic_year="2026/2027",
            semester=1,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=20),
            status=PeriodStatus.OPEN,
        )
    )
    db_session.add_all([Discipline(id=i, name=f"Дисциплина {i}", department_id=2) for i in (1, 2)])
    db_session.add(StudyGroup(id=1, name="261-001", department_id=2))
    await db_session.flush()
    db_session.add_all(
        [
            GroupPeriod(group_id=1, period_id=1),
            GroupRecommendation(
                group_id=1,
                period_id=1,
                recommended=True,
                version=1,
                changed_by_id=1,
                changed_at=__import__("datetime").datetime.now(),
            ),
            Student(id=1, full_name="Студент", group_id=1),
        ]
    )
    await db_session.commit()
    context = {"actor": UserRead.model_validate(users[0]), "users": users, "session": db_session}
    application.dependency_overrides[get_current_user] = lambda: context["actor"]
    yield context
    application.dependency_overrides.pop(get_current_user, None)


async def prepare_test(client, context):
    context["actor"] = UserRead.model_validate(context["users"][1])
    response = await client.put(
        "/api/workflow/participation",
        json={"group_id": 1, "period_id": 1, "participates": True, "discipline_ids": [1, 2]},
    )
    assert response.status_code == 200, response.text
    tests = (await client.get("/api/testing?period_id=1")).json()
    identifier = tests[0]["id"]
    response = await client.put(
        f"/api/workflow/testing/{identifier}/assignment",
        json={
            "teacher_id": 3,
            "scheduled_at": date.today().isoformat() + "T12:00:00",
            "room": "А-101",
        },
    )
    assert response.status_code == 200, response.text
    context["actor"] = UserRead.model_validate(context["users"][2])
    assert (
        await client.put(f"/api/workflow/testing/{identifier}/agreement", json={"approved": True})
    ).status_code == 200
    assert (
        await client.put(
            "/api/results",
            json={
                "knowledge_test_id": identifier,
                "student_id": 1,
                "intermediate_result": 4,
                "testing_result": 4,
                "participation_status": "PASSED",
            },
        )
    ).status_code == 200
    assert (await client.post(f"/api/results/complete/{identifier}")).status_code == 200
    return identifier


async def test_full_report_lifecycle(client, workflow):
    identifier = await prepare_test(client, workflow)
    document = await client.get(f"/api/exports/report/{identifier}.docx")
    assert document.status_code == 200, document.text
    assert "word/document.xml" in ZipFile(io.BytesIO(document.content)).namelist()
    report = await client.post(f"/api/report-workflow/testing/{identifier}")
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]
    uploaded = await client.post(
        f"/api/report-workflow/{report_id}/file",
        files={"file": ("report.docx", document.content, "application/octet-stream")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["electronic_status"] == "SUBMITTED"
    assert (await client.get(f"/api/report-workflow/{report_id}/file")).content == document.content
    assert (
        await client.put(
            f"/api/report-workflow/{report_id}/review/electronic", json={"approved": True}
        )
    ).status_code == 403
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    assert (
        await client.put(f"/api/report-workflow/{report_id}/review/paper", json={"approved": True})
    ).status_code == 409
    assert (
        await client.put(
            f"/api/report-workflow/{report_id}/review/electronic", json={"approved": False}
        )
    ).status_code == 422
    rejected = await client.put(
        f"/api/report-workflow/{report_id}/review/electronic",
        json={"approved": False, "comment": "Исправьте подпись"},
    )
    assert rejected.json()["electronic_status"] == "REJECTED"
    assert (
        await client.put(
            f"/api/report-workflow/{report_id}/review/electronic", json={"approved": True}
        )
    ).status_code == 409
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert (
        await client.post(
            f"/api/report-workflow/{report_id}/file",
            files={"file": ("report.docx", document.content, "application/octet-stream")},
        )
    ).status_code == 200
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    approved = await client.put(
        f"/api/report-workflow/{report_id}/review/electronic", json={"approved": True}
    )
    assert approved.json()["electronic_comment"] is None
    final = await client.put(
        f"/api/report-workflow/{report_id}/review/paper", json={"approved": True}
    )
    assert final.json()["final_status"] == "COMPLETE"


async def test_closed_period_blocks_changes(client, workflow):
    identifier = await prepare_test(client, workflow)
    period = await workflow["session"].get(Period, 1)
    period.status = PeriodStatus.CLOSED
    await workflow["session"].commit()
    response = await client.put(
        "/api/results",
        json={
            "knowledge_test_id": identifier,
            "student_id": 1,
            "testing_result": 5,
            "participation_status": "PASSED",
        },
    )
    assert response.status_code == 409


async def test_roster_and_scope_are_enforced(client, workflow):
    identifier = await prepare_test(client, workflow)
    workflow["actor"] = UserRead.model_validate(workflow["users"][3])
    assert (await client.get(f"/api/workflow/testing/{identifier}/roster")).status_code == 403
    assert (await client.get(f"/api/testing/{identifier}")).status_code == 403
    assert (await client.get("/api/testing?period_id=1")).status_code == 403


async def test_foreign_department_assignment_and_teacher_ownership(client, workflow):
    session = workflow["session"]
    session.add(
        Department(id=3, name="Другая кафедра", parent_id=1, type=DepartmentType.DEPARTMENT)
    )
    await session.flush()
    foreign_chair = User(
        id=5, full_name="Другой заведующий", role=UserRole.CHAIR_HEAD, department_id=3
    )
    foreign_teacher = User(
        id=6, full_name="Другой преподаватель", role=UserRole.TEACHER, department_id=3
    )
    session.add_all([foreign_chair, foreign_teacher])
    discipline = await session.get(Discipline, 2)
    discipline.department_id = 3
    await session.commit()
    workflow["actor"] = UserRead.model_validate(workflow["users"][1])
    assert (
        await client.put(
            "/api/workflow/participation",
            json={"group_id": 1, "period_id": 1, "participates": True, "discipline_ids": [1, 2]},
        )
    ).status_code == 200
    tests = (await client.get("/api/testing?period_id=1")).json()
    identifier = next(row["id"] for row in tests if row["discipline_id"] == 2)
    assignment = {
        "teacher_id": 6,
        "scheduled_at": date.today().isoformat() + "T14:00:00",
        "room": "Б-202",
    }
    assert (
        await client.put(f"/api/workflow/testing/{identifier}/assignment", json=assignment)
    ).status_code == 403
    workflow["actor"] = UserRead.model_validate(foreign_chair)
    assert (
        await client.put(f"/api/workflow/testing/{identifier}/assignment", json=assignment)
    ).status_code == 200
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert (await client.get(f"/api/testing/{identifier}")).status_code == 403
    assert (await client.get(f"/api/workflow/testing/{identifier}/roster")).status_code == 403
    assert (
        await client.put(f"/api/workflow/testing/{identifier}/agreement", json={"approved": True})
    ).status_code == 403
    workflow["actor"] = UserRead.model_validate(foreign_teacher)
    assert (
        await client.put(f"/api/workflow/testing/{identifier}/agreement", json={"approved": True})
    ).status_code == 200


async def test_users_and_requests(client, workflow):
    workflow["actor"] = UserRead.model_validate(workflow["users"][3])
    assert (await client.get("/api/administration/users")).status_code == 403
    request = await client.post(
        "/api/administration/access-requests",
        json={"requested_role": "TEACHER", "reason": "Преподаю дисциплину"},
    )
    assert request.status_code == 201
    assert (
        await client.post(
            "/api/administration/access-requests",
            json={"requested_role": "TEACHER", "reason": "Повтор"},
        )
    ).status_code == 409
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    result = await client.put(
        f"/api/administration/access-requests/{request.json()['id']}", json={"approved": True}
    )
    assert result.status_code == 200
    await workflow["session"].refresh(workflow["users"][3])
    assert workflow["users"][3].role == UserRole.TEACHER


async def test_orders_are_persisted_and_published_orders_immutable(client, workflow):
    payload = {
        "title": "О проведении проверки",
        "year": "2026/2027",
        "semester": "Осень",
        "date": date.today().isoformat(),
        "draft": True,
        "period_id": 1,
    }
    order = await client.post("/api/orders", json=payload)
    assert order.status_code == 201, order.text
    identifier = order.json()["id"]
    assert (
        await client.put(f"/api/orders/{identifier}", json={**payload, "draft": False})
    ).status_code == 200
    assert (await client.delete(f"/api/orders/{identifier}")).status_code == 409
    assert any(row["id"] == identifier for row in (await client.get("/api/orders")).json())


async def test_department_cycles_and_references(client, workflow):
    response = await client.put(
        "/api/department-management/1",
        json={"name": "Факультет", "parent_id": 2, "type": "FACULTY"},
    )
    assert response.status_code == 422
    assert (await client.delete("/api/department-management/2")).status_code == 409


async def test_dashboard_counts_and_pdf(client, workflow):
    await prepare_test(client, workflow)
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    dashboard = await client.get("/api/dashboard?period_id=1")
    assert dashboard.status_code == 200, dashboard.text
    row = dashboard.json()["departments"][0]
    assert row["groups"] == {"required": 1, "actual": 1}
    assert row["disciplines"] == {"required": 2, "actual": 2}
    assert row["all_submitted"] is False
    response = await client.get("/api/exports/schedule/1.pdf")
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")


async def test_import_is_atomic_and_preserves_existing_roles(client, workflow):
    content = "external_id;full_name;department_id\nnew-1;Новый сотрудник;2\n".encode()
    response = await client.post(
        "/api/administration/imports/employees", files={"file": ("staff.csv", content)}
    )
    assert response.status_code == 200, response.text
    assert response.json()["records_processed"] == 1
    records = (await client.get("/api/administration/users")).json()
    user = next(row for row in records if row["external_id"] == "new-1")
    assert user["role"] == "GUEST"
    broken = "external_id;full_name;department_id\nnew-2;Сотрудник;999\n".encode()
    response = await client.post(
        "/api/administration/imports/employees", files={"file": ("staff.csv", broken)}
    )
    assert response.status_code == 422, response.text
    records = (await client.get("/api/administration/users")).json()
    assert not any(row["external_id"] == "new-2" for row in records)
    logs = (await client.get("/api/administration/imports")).json()
    assert logs[0]["status"] == "FAILED"


async def test_auth_dev_sessions_and_production_lock(client, workflow, application):
    application.dependency_overrides.pop(get_current_user)
    response = await client.post("/api/auth/dev-login", json={"user_id": 3})
    assert response.status_code == 200, response.text
    assert (await client.get("/api/auth/me")).json()["id"] == 3
    token = client.cookies.get("dev_session")
    assert (await client.post("/api/auth/logout")).status_code == 204
    client.cookies.set("dev_session", token)
    assert (await client.get("/api/auth/me")).status_code == 403
    await client.post("/api/auth/dev-login", json={"user_id": 3})
    from app.core.config import Settings

    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, APP_ENV="production"
    )
    assert (await client.post("/api/auth/dev-login", json={"user_id": 1})).status_code == 403
    assert (await client.get("/api/auth/dev-users")).status_code == 403
    assert (await client.get("/api/auth/me")).status_code == 403


async def test_summary_contains_saved_results(client, workflow):
    await prepare_test(client, workflow)
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    response = await client.get("/api/exports/summary/1.csv")
    assert response.status_code == 200, response.text
    text = response.content.decode("utf-8-sig")
    assert "Группа" in text and "261-001" in text


async def test_catalog_creation_references_and_role_scope(client, workflow):
    response = await client.post(
        "/api/catalog/programs", json={"name": "Информатика", "code": "09.03.01", "faculty_id": 1}
    )
    assert response.status_code == 201, response.text
    program_id = response.json()["id"]
    response = await client.post(
        "/api/catalog/groups",
        json={
            "name": "261-002",
            "department_id": 2,
            "study_program_id": program_id,
            "admission_year": 2026,
            "period_ids": [1],
        },
    )
    assert response.status_code == 201, response.text
    group_id = response.json()["id"]
    response = await client.post(
        "/api/students", json={"full_name": "Новый студент", "group_id": group_id}
    )
    assert response.status_code == 201, response.text
    response = await client.post(
        "/api/disciplines", json={"name": "Новая дисциплина", "department_id": 2}
    )
    assert response.status_code == 201, response.text
    assert (
        await client.post("/api/catalog/groups", json={"name": "Ошибка", "period_ids": [999]})
    ).status_code == 404
    assert (
        await client.post("/api/students", json={"full_name": "Ошибка", "group_id": 999})
    ).status_code == 404
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert (
        await client.post("/api/catalog/programs", json={"name": "Запрещено", "faculty_id": 1})
    ).status_code == 403
    assert (await client.get("/api/students")).status_code == 403
