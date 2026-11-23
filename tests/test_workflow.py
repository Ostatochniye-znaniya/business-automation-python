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
            paper_reports_required=True,
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


async def test_dean_reviews_only_own_faculty_reports(client, workflow):
    from app.modules.reports.models import Report
    from app.modules.testing.models import KnowledgeTest

    identifier = await prepare_test(client, workflow)
    created = await client.post(f"/api/report-workflow/testing/{identifier}")
    report_id = created.json()["id"]
    document = await client.get(f"/api/exports/report/{identifier}.docx")
    assert (
        await client.post(
            f"/api/report-workflow/{report_id}/file",
            files={"file": ("report.docx", document.content)},
        )
    ).status_code == 200
    session = workflow["session"]
    session.add(Department(id=3, name="Другой факультет", type=DepartmentType.FACULTY))
    await session.flush()
    session.add(StudyGroup(id=2, name="Чужая группа", department_id=3))
    dean = User(id=5, full_name="Декан", role=UserRole.DEPARTMENT_HEAD, department_id=1)
    session.add(dean)
    await session.flush()
    foreign_test = KnowledgeTest(period_id=1, group_id=2, discipline_id=1)
    session.add(foreign_test)
    await session.flush()
    foreign_report = Report(knowledge_test_id=foreign_test.id, electronic_status="DRAFT")
    session.add(foreign_report)
    await session.commit()
    workflow["actor"] = UserRead.model_validate(dean)
    assert (
        await client.put(
            f"/api/report-workflow/{report_id}/review/electronic", json={"approved": True}
        )
    ).status_code == 200
    assert (
        await client.put(
            f"/api/report-workflow/{foreign_report.id}/review/electronic", json={"approved": True}
        )
    ).status_code == 403
    await session.refresh(foreign_report)
    assert foreign_report.electronic_status == "DRAFT"


async def test_orders_are_persisted_and_published_orders_immutable(client, workflow):
    payload = {
        "title": "О проведении проверки",
        "number": "42-ОД",
        "year": "2026/2027",
        "semester": "Осень",
        "date": date.today().isoformat(),
        "draft": True,
        "period_id": 1,
    }
    order = await client.post("/api/orders", json=payload)
    assert order.status_code == 201, order.text
    identifier = order.json()["id"]
    assert (await client.get(f"/api/orders/{identifier}/file")).status_code == 409
    assert (
        await client.put(f"/api/orders/{identifier}", json={**payload, "draft": False})
    ).status_code == 422
    payload["details"] = {
        "bossControl": "Иванов Иван Иванович",
        "bossMethod": "Петров Пётр Петрович",
        **{
            key: date.today().isoformat()
            for key in [
                "checkSummaryDate",
                "surveySummaryDate",
                "electronicReportDeadline",
                "paperReportDeadline",
                "testingStartDate",
                "testingEndDate",
                "surveyStartDate",
                "surveyEndDate",
                "preparationStartDate",
                "preparationEndDate",
                "resultsProcessingStartDate",
            ]
        },
    }
    assert (
        await client.put(f"/api/orders/{identifier}", json={**payload, "draft": False})
    ).status_code == 200
    assert (await client.delete(f"/api/orders/{identifier}")).status_code == 409
    document = await client.get(f"/api/orders/{identifier}/file")
    assert document.status_code == 200, document.text
    assert document.content.startswith(b"%PDF")
    assert (await client.put(f"/api/orders/{identifier}", json=payload)).status_code == 409
    assert any(row["id"] == identifier for row in (await client.get("/api/orders")).json())


async def test_order_date_validation_and_paper_policy(client, workflow):
    from app.core.exceptions import ValidationError
    from app.modules.orders.schemas import OrderCreate
    from app.modules.orders.service import OrderService

    period = await workflow["session"].get(Period, 1)
    details = {
        "bossControl": "Иванов",
        "bossMethod": "Петров",
        **{
            key: date.today().isoformat()
            for key in [
                "checkSummaryDate",
                "surveySummaryDate",
                "electronicReportDeadline",
                "testingStartDate",
                "testingEndDate",
                "surveyStartDate",
                "surveyEndDate",
                "preparationStartDate",
                "preparationEndDate",
                "resultsProcessingStartDate",
            ]
        },
    }
    data = OrderCreate(
        title="Проверка",
        number="43-ОД",
        year=period.academic_year,
        semester="Осень",
        date=date.today(),
        period_id=1,
        draft=False,
        details=details,
    )
    with pytest.raises(ValidationError, match="бумажных"):
        OrderService.validate_publication(data, period)
    period.paper_reports_required = False
    OrderService.validate_publication(data, period)
    data.details["testingEndDate"] = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError, match="последовательность"):
        OrderService.validate_publication(data, period)


async def test_report_templates_before_results_and_scoped_download(client, workflow):
    from docx import Document

    identifier = await prepare_test(client, workflow)
    from app.modules.testing.models import KnowledgeTest

    test = await workflow["session"].get(KnowledgeTest, identifier)
    test.status = "PLANNED"
    await workflow["session"].commit()
    document = await client.get(f"/api/exports/report/{identifier}.docx?template=true")
    assert document.status_code == 200, document.text
    parsed = Document(io.BytesIO(document.content))
    assert len(parsed.tables) == 2
    assert parsed.tables[0].rows[7].cells[1].text == "Студент"
    assert parsed.tables[0].rows[7].cells[3].text == ""
    assert (await client.get(f"/api/exports/report/{identifier}.docx")).status_code == 422
    preview = await client.get(f"/api/exports/report/{identifier}.pdf?template=true")
    assert preview.status_code == 200 and preview.content.startswith(b"%PDF")
    workflow["actor"] = UserRead.model_validate(workflow["users"][3])
    assert (
        await client.get(f"/api/exports/report/{identifier}.docx?template=true")
    ).status_code == 403


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


async def test_report_participation_threshold_uses_the_whole_roster(client, workflow):
    identifier = await prepare_test(client, workflow)
    session = workflow["session"]
    session.add_all([Student(id=i, full_name=f"Студент {i}", group_id=1) for i in (2, 3, 4)])
    await session.commit()
    row = next(
        row
        for row in (await client.get("/api/reports/overview?period_id=1")).json()
        if row["knowledge_test_id"] == identifier
    )
    assert (
        row["total_students"],
        row["participated_students"],
        row["at_least_half_participated"],
    ) == (4, 1, False)
    assert row["participation_percentage"] == 25
    response = await client.put(
        "/api/results",
        json={
            "knowledge_test_id": identifier,
            "student_id": 2,
            "testing_result": 0,
            "participation_status": "PASSED",
        },
    )
    assert response.status_code == 200, response.text
    for student_id, status in [(3, "ABSENT"), (4, "NOT_ADMITTED")]:
        assert (
            await client.put(
                "/api/results",
                json={
                    "knowledge_test_id": identifier,
                    "student_id": student_id,
                    "participation_status": status,
                },
            )
        ).status_code == 200
    row = next(
        row
        for row in (await client.get("/api/reports/overview?period_id=1")).json()
        if row["knowledge_test_id"] == identifier
    )
    assert row["at_least_half_participated"] is True
    assert row["participation_percentage"] == 50


async def test_report_participation_for_empty_group_is_false(client, workflow):
    from sqlalchemy import delete

    await workflow["session"].execute(delete(Student))
    await workflow["session"].commit()
    assert (
        await client.put(
            "/api/workflow/participation",
            json={"group_id": 1, "period_id": 1, "participates": True, "discipline_ids": [1, 2]},
        )
    ).status_code == 200
    rows = (await client.get("/api/reports/overview")).json()
    assert len(rows) == 2
    assert all(
        row["total_students"] == 0 and row["at_least_half_participated"] is False for row in rows
    )


async def test_paper_policy_recalculates_existing_reports_and_protects_writes(client, workflow):
    identifier = await prepare_test(client, workflow)
    report = (await client.post(f"/api/report-workflow/testing/{identifier}")).json()
    document = await client.get(f"/api/exports/report/{identifier}.docx")
    assert (
        await client.post(
            f"/api/report-workflow/{report['id']}/file",
            files={"file": ("report.docx", document.content)},
        )
    ).status_code == 200
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    path = f"/api/report-workflow/{report['id']}/review/"
    assert (await client.put(path + "electronic", json={"approved": True})).json()[
        "final_status"
    ] == "PENDING"
    assert (
        await client.patch("/api/periods/1/report-policy", json={"paper_reports_required": False})
    ).status_code == 200
    assert (await client.get(f"/api/reports/{report['id']}")).json()["final_status"] == "COMPLETE"
    row = (await client.get("/api/reports/overview")).json()[0]
    assert row["paper_status"] == "NOT_REQUIRED"
    assert (await client.put(path + "paper", json={"approved": True})).status_code == 409
    assert (
        await client.patch("/api/periods/1/report-policy", json={"paper_reports_required": True})
    ).status_code == 200
    assert (await client.get(f"/api/reports/{report['id']}")).json()["final_status"] == "PENDING"
    assert (await client.put(path + "paper", json={"approved": True})).json()[
        "final_status"
    ] == "COMPLETE"
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert (
        await client.patch("/api/periods/1/report-policy", json={"paper_reports_required": False})
    ).status_code == 403


async def test_reports_faculty_scope_and_department_discipline_filters(client, workflow):
    from app.modules.testing.models import KnowledgeTest

    identifier = await prepare_test(client, workflow)
    session = workflow["session"]
    session.add(Department(id=3, name="Другой факультет", type=DepartmentType.FACULTY))
    await session.flush()
    session.add(StudyGroup(id=2, name="Чужая группа", department_id=3))
    dean = User(id=5, full_name="Декан", role=UserRole.DEPARTMENT_HEAD, department_id=1)
    session.add(dean)
    await session.flush()
    foreign = KnowledgeTest(period_id=1, group_id=2, discipline_id=1)
    session.add(foreign)
    await session.commit()
    workflow["actor"] = UserRead.model_validate(workflow["users"][0])
    rows = (await client.get("/api/reports/overview?period_id=1")).json()
    assert len(rows) == 3
    assert (
        len((await client.get("/api/reports/overview?department_id=2&discipline_id=1")).json()) == 2
    )
    assert len((await client.get("/api/reports/overview?faculty_id=3")).json()) == 1
    workflow["actor"] = UserRead.model_validate(dean)
    rows = (await client.get("/api/reports/overview?period_id=1")).json()
    assert len(rows) == 2 and all(row["faculty_id"] == 1 for row in rows)
    assert (await client.get("/api/reports/overview?faculty_id=3")).json() == []
    assert (await client.get(f"/api/testing/{foreign.id}")).status_code == 403
    assert (await client.get(f"/api/testing/{identifier}")).status_code == 200


async def test_dean_can_read_group_linked_to_faculty_only_via_program(client, workflow):
    from app.modules.groups.models import StudyProgram
    from app.modules.testing.models import KnowledgeTest

    session = workflow["session"]
    session.add(StudyProgram(id=1, name="Направление", faculty_id=1))
    await session.flush()
    session.add(StudyGroup(id=2, name="Группа направления", study_program_id=1))
    dean = User(id=5, full_name="Декан", role=UserRole.DEPARTMENT_HEAD, department_id=1)
    session.add(dean)
    await session.flush()
    test = KnowledgeTest(period_id=1, group_id=2, discipline_id=1)
    session.add(test)
    await session.commit()
    workflow["actor"] = UserRead.model_validate(dean)
    assert (await client.get(f"/api/testing/{test.id}")).status_code == 200
    assert len((await client.get("/api/reports/overview")).json()) == 1


async def create_multi_test(client, workflow):
    session = workflow["session"]
    teacher = User(id=5, full_name="Второй преподаватель", role=UserRole.TEACHER, department_id=2)
    session.add(teacher)
    await session.commit()
    workflow["actor"] = UserRead.model_validate(workflow["users"][1])
    response = await client.put(
        "/api/workflow/participation",
        json={"group_id": 1, "period_id": 1, "participates": True, "discipline_ids": [1, 2]},
    )
    assert response.status_code == 200, response.text
    test_id = (await client.get("/api/testing?period_id=1")).json()[0]["id"]
    window = {
        "teacher_ids": [3, 5],
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=2)).isoformat(),
        "room": "101",
    }
    response = await client.put(f"/api/workflow/testing/{test_id}/assignments", json=window)
    assert response.status_code == 200, response.text
    return test_id, teacher, window


async def test_multiple_teachers_have_independent_dates_and_decisions(client, workflow):
    test_id, teacher, window = await create_multi_test(client, workflow)
    base = f"/api/workflow/testing/{test_id}"
    eligible = (await client.get(base + "/eligible-teachers")).json()
    assert {row["id"] for row in eligible} == {3, 5}
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert len((await client.get("/api/testing?period_id=1")).json()) == 1
    assert (await client.put(base + "/agreement", json={"approved": True})).status_code == 422
    assert (
        await client.put(
            base + "/agreement",
            json={
                "approved": True,
                "scheduled_at": (date.today() + timedelta(days=3)).isoformat() + "T12:00:00",
            },
        )
    ).status_code == 422
    result = await client.put(
        base + "/agreement",
        json={
            "approved": True,
            "scheduled_at": date.today().isoformat() + "T12:00:00",
        },
    )
    assert result.status_code == 200, result.text
    decisions = {a["teacher_id"]: a["agreement_status"] for a in result.json()["assignments"]}
    assert decisions == {3: "AGREED", 5: "PROPOSED"}
    workflow["actor"] = UserRead.model_validate(teacher)
    assert len((await client.get("/api/testing?period_id=1")).json()) == 1
    assert len((await client.get("/api/reports/overview?period_id=1")).json()) == 1
    assert (await client.get(base + "/roster")).status_code == 200
    rejected = await client.put(base + "/agreement", json={"approved": False, "comment": "Занят"})
    assert rejected.status_code == 200, rejected.text
    decisions = {a["teacher_id"]: a["agreement_status"] for a in rejected.json()["assignments"]}
    assert decisions == {3: "AGREED", 5: "REJECTED"}
    approved = await client.put(
        base + "/agreement",
        json={
            "approved": True,
            "scheduled_at": (date.today() + timedelta(days=1)).isoformat() + "T14:00:00",
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["agreement_status"] == "AGREED"
    # Both names appear in report metadata; each selected date is preserved.
    row = (await client.get("/api/reports/overview?period_id=1")).json()[0]
    assert "Второй преподаватель" in row["teacher_name"]
    dates = {a["scheduled_at"] for a in approved.json()["assignments"]}
    assert len(dates) == 2
    assert (
        await client.get(f"/api/exports/report/{test_id}.docx?template=true")
    ).status_code == 200
    # Saving the unchanged list preserves existing decisions.
    workflow["actor"] = UserRead.model_validate(workflow["users"][1])
    unchanged = await client.put(base + "/assignments", json=window)
    assert unchanged.json()["agreement_status"] == "AGREED"
    # Removing a teacher revokes all access without modifying the other decision.
    removed = await client.put(base + "/assignments", json={**window, "teacher_ids": [3]})
    assert removed.status_code == 200, removed.text
    assert removed.json()["assignments"][0]["agreement_status"] == "AGREED"
    workflow["actor"] = UserRead.model_validate(teacher)
    assert (await client.get("/api/testing?period_id=1")).json() == []
    assert (await client.get(f"/api/testing/{test_id}")).status_code == 403
    assert (
        await client.get(f"/api/exports/report/{test_id}.docx?template=true")
    ).status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"teacher_ids": [3, 3]},
        {"teacher_ids": []},
        {"teacher_ids": [1]},
        {"teacher_ids": [999]},
        {"start_date": "2020-01-01"},
        {"end_date": "2020-01-01"},
    ],
)
async def test_assignment_list_validation(client, workflow, changes):
    test_id, _, window = await create_multi_test(client, workflow)
    response = await client.put(
        f"/api/workflow/testing/{test_id}/assignments", json={**window, **changes}
    )
    assert response.status_code == 422, response.text
    rows = (await client.get(f"/api/workflow/testing/{test_id}/assignments")).json()
    assert {a["teacher_id"] for a in rows} == {3, 5}


async def test_second_teacher_collision_is_detected(client, workflow):
    test_id, teacher, _ = await create_multi_test(client, workflow)
    workflow["actor"] = UserRead.model_validate(teacher)
    response = await client.put(
        f"/api/workflow/testing/{test_id}/agreement",
        json={
            "approved": True,
            "scheduled_at": date.today().isoformat() + "T12:00:00",
        },
    )
    assert response.status_code == 200, response.text
    workflow["actor"] = UserRead.model_validate(workflow["users"][1])
    other = next(
        t for t in (await client.get("/api/testing?period_id=1")).json() if t["id"] != test_id
    )
    response = await client.put(
        f"/api/workflow/testing/{other['id']}/assignment",
        json={
            "teacher_id": 3,
            "scheduled_at": date.today().isoformat() + "T12:00:00",
            "room": "102",
        },
    )
    assert response.status_code == 409, response.text


async def test_faculty_schedule_submission_rejection_and_resubmission(client, workflow):
    session = workflow["session"]
    responsible = User(
        id=5, full_name="Ответственный", role=UserRole.DEPARTMENT_RESPONSIBLE, department_id=1
    )
    dean = User(id=6, full_name="Декан", role=UserRole.DEPARTMENT_HEAD, department_id=1)
    foreign_dean = User(
        id=7, full_name="Чужой декан", role=UserRole.DEPARTMENT_HEAD, department_id=2
    )
    session.add_all([responsible, dean, foreign_dean])
    await session.commit()
    base = "/api/report-workflow/schedules/1/1"
    original = b"%PDF-1.4\nfirst schedule"
    corrected = b"%PDF-1.4\ncorrected schedule"
    workflow["actor"] = UserRead.model_validate(responsible)
    assert (await client.get(base)).status_code == 404
    assert (
        await client.post(base + "/file", files={"file": ("bad.docx", original)})
    ).status_code == 422
    assert (
        await client.post(base + "/file", files={"file": ("bad.pdf", b"not PDF")})
    ).status_code == 422
    uploaded = await client.post(base + "/file", files={"file": ("schedule.pdf", original)})
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["status"] == "SUBMITTED"
    assert (await client.put(base + "/review", json={"approved": True})).status_code == 403
    assert (
        await client.post(base + "/file", files={"file": ("schedule.pdf", corrected)})
    ).status_code == 409
    workflow["actor"] = UserRead.model_validate(foreign_dean)
    assert (await client.get(base)).status_code == 403
    assert (await client.get(base + "/file")).status_code == 403
    assert (await client.put(base + "/review", json={"approved": True})).status_code == 403
    workflow["actor"] = UserRead.model_validate(dean)
    assert (await client.get(base + "/file")).content == original
    assert (
        await client.put(base + "/review", json={"approved": False, "comment": "  "})
    ).status_code == 422
    rejected = await client.put(
        base + "/review", json={"approved": False, "comment": " Исправьте даты "}
    )
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["comment"] == "Исправьте даты"
    assert (await client.put(base + "/review", json={"approved": True})).status_code == 409
    workflow["actor"] = UserRead.model_validate(responsible)
    replaced = await client.post(base + "/file", files={"file": ("schedule.pdf", corrected)})
    assert replaced.json()["id"] == uploaded.json()["id"]
    assert replaced.json()["status"] == "SUBMITTED" and replaced.json()["comment"] is None
    workflow["actor"] = UserRead.model_validate(dean)
    assert (await client.get(base + "/file")).content == corrected
    approved = await client.put(base + "/review", json={"approved": True})
    assert approved.json()["status"] == "APPROVED"
    workflow["actor"] = UserRead.model_validate(responsible)
    assert (
        await client.post(base + "/file", files={"file": ("schedule.pdf", original)})
    ).status_code == 409
    workflow["actor"] = UserRead.model_validate(workflow["users"][2])
    assert (await client.get(base)).status_code == 403
    assert (await client.get(base + "/file")).status_code == 403


async def test_assignment_migration_preserves_old_reports_and_results(client, workflow):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import select

    from app.modules.reports.models import FacultySchedule
    from app.modules.testing.models import KnowledgeTest
    from app.modules.testing.models import TestAssignment as Assignment

    test_id = await prepare_test(client, workflow)
    report = (await client.post(f"/api/report-workflow/testing/{test_id}")).json()
    document = await client.get(f"/api/exports/report/{test_id}.docx")
    assert (
        await client.post(
            f"/api/report-workflow/{report['id']}/file",
            files={"file": ("report.docx", document.content)},
        )
    ).status_code == 200
    session = workflow["session"]
    old_test = await session.get(KnowledgeTest, test_id)
    old_date = old_test.scheduled_at
    await session.commit()
    session.expunge_all()
    migration_path = (
        Path(__file__).parents[1] / "migrations/versions/0008_assignments_and_schedules.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0008", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    def upgrade(connection):
        # Recreate the pre-migration database while retaining its checks/reports/results.
        FacultySchedule.__table__.drop(connection)
        Assignment.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

    connection = await session.connection()
    await connection.run_sync(upgrade)
    await session.commit()
    assignment = await session.scalar(
        select(Assignment).where(Assignment.knowledge_test_id == test_id)
    )
    assert assignment.teacher_id == 3
    assert assignment.scheduled_at == old_date
    assert assignment.agreement_status == "AGREED"
    assert assignment.start_date is None and assignment.end_date is None
    assert (await client.get(f"/api/testing/{test_id}")).status_code == 200
    assert (
        await client.get(f"/api/report-workflow/{report['id']}/file")
    ).content == document.content
    assert (await client.get(f"/api/exports/report/{test_id}.docx")).status_code == 200
    rows = (await client.get("/api/reports/overview?period_id=1")).json()
    assert rows[0]["report_id"] == report["id"]
    assert rows[0]["participated_students"] == 1
