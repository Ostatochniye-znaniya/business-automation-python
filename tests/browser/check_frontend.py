"""Real HTTP and browser walkthrough using disposable SQLite data.

Run after frontend build: python tests/browser/check_frontend.py --output <directory>
Requires Playwright and Microsoft Edge (or Playwright Chromium).
"""

import argparse
import asyncio
import os
import shutil
import socket
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from playwright.async_api import async_playwright, expect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


async def run(output: Path):
    os.environ.update(SERVE_FRONTEND="false", APP_ENV="test", DEMO_DATA="false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.core.enums import DepartmentType, TestingPeriodStatus, UserRole
    from app.db.base import Base
    from app.db.dependencies import get_db_session
    from app.main import create_app
    from app.modules.departments.models import Department
    from app.modules.disciplines.models import Discipline
    from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
    from app.modules.groups.recommendation_models import GroupRecommendation
    from app.modules.periods.models import TestingPeriod
    from app.modules.students.models import Student
    from app.modules.testing.models import KnowledgeTest
    from app.modules.users.models import User

    with TemporaryDirectory(prefix="knowledge-browser-") as directory:
        os.environ["REPORT_STORAGE_DIR"] = str(Path(directory) / "reports")
        get_settings.cache_clear()
        app = create_app()
        engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(directory) / "test.db"))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(
                Department(
                    id=1, name="Факультет информационных технологий", type=DepartmentType.FACULTY
                )
            )
            await session.flush()
            session.add(
                Department(
                    id=2, name="Кафедра информатики", parent_id=1, type=DepartmentType.DEPARTMENT
                )
            )
            await session.flush()
            session.add_all(
                [
                    User(id=1, full_name="Тестовый администратор", role=UserRole.ADMIN),
                    User(
                        id=4,
                        full_name="Тестовый декан",
                        role=UserRole.DEPARTMENT_HEAD,
                        department_id=1,
                    ),
                    User(
                        id=2,
                        full_name="Тестовый заведующий",
                        role=UserRole.CHAIR_HEAD,
                        department_id=2,
                    ),
                    User(
                        id=3,
                        full_name="Тестовый преподаватель",
                        role=UserRole.TEACHER,
                        department_id=2,
                    ),
                ]
            )
            session.add(
                TestingPeriod(
                    id=1,
                    name="Осенний период",
                    academic_year="2026/2027",
                    semester=1,
                    start_date=date.today() - timedelta(days=1),
                    end_date=date.today() + timedelta(days=60),
                    status=TestingPeriodStatus.OPEN,
                )
            )
            session.add(
                StudyProgram(
                    id=1, name="Информатика и вычислительная техника", code="09.03.01", faculty_id=1
                )
            )
            await session.flush()
            session.add(StudyGroup(id=1, name="261-001", department_id=2, study_program_id=1))
            session.add_all(
                [
                    Discipline(id=1, name="Базы данных", department_id=2),
                    Discipline(id=2, name="Программирование", department_id=2),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    *[
                        Student(id=i, full_name=f"Тестовый студент {i}", group_id=1)
                        for i in range(1, 5)
                    ],
                    GroupPeriod(group_id=1, period_id=1),
                    GroupRecommendation(
                        group_id=1,
                        period_id=1,
                        recommended=True,
                        version=1,
                        changed_by_id=1,
                        changed_at=datetime.now(),
                    ),
                ]
            )
            session.add(Department(id=3, name="Другой факультет", type=DepartmentType.FACULTY))
            await session.flush()
            session.add(StudyGroup(id=2, name="Чужая группа", department_id=3))
            await session.flush()
            session.add(KnowledgeTest(id=900, period_id=1, group_id=2, discipline_id=2))
            await session.commit()

        async def dependency():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db_session] = dependency

        @asynccontextmanager
        async def lifespan(application):
            yield

        app.router.lifespan_context = lifespan
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 8001))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning")
        )
        task = asyncio.create_task(server.serve())
        while not server.started:
            await asyncio.sleep(0.05)
        output.mkdir(parents=True, exist_ok=True)
        log = (output / "next.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                shutil.which("node") or "node",
                str(ROOT / "frontend/node_modules/next/dist/bin/next"),
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT / "frontend",
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"},
        )
        base = f"http://127.0.0.1:{port}/csh"
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                for _ in range(200):
                    if process.poll() is not None:
                        raise RuntimeError("Next.js failed; see next.log")
                    try:
                        if (await client.get(base + "/login")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise RuntimeError("Next.js startup timeout")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    **(
                        {"channel": "msedge"}
                        if Path(
                            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
                        ).is_file()
                        else {}
                    )
                )
                page = await browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                async def login(identifier):
                    await page.goto(base + "/login")
                    await page.get_by_label("Сотрудник", exact=True).select_option(str(identifier))
                    await page.get_by_role("button", name="Войти", exact=True).click()
                    await page.wait_for_url(lambda url: "/login" not in url)
                    await expect(page.locator(".navbar-user-name")).not_to_be_empty()

                async def mutation(path, work):
                    async with page.expect_response(
                        lambda response: (
                            path in response.url
                            and response.request.method in {"POST", "PUT", "PATCH"}
                        )
                    ) as pending:
                        await work()
                    response = await pending.value
                    assert response.ok, (response.status, await response.text())

                async def choose(label, option, endpoint="/reports/overview?", query_key=None):
                    await page.get_by_role("button", name=label, exact=True).click()
                    query_key = query_key or (
                        "discipline_id=1" if label == "Дисциплина" else "department_id=2"
                    )
                    async with page.expect_response(
                        lambda response: (
                            endpoint in response.url
                            and query_key in response.url
                            and response.request.method == "GET"
                        )
                    ):
                        await page.get_by_role("option", name=option, exact=True).click()
                    await expect(
                        page.get_by_text("Загрузка отчётов…", exact=True)
                    ).not_to_be_visible()

                async def details():
                    await page.get_by_role("button", name="Подробнее", exact=True).first.click()
                    return page.get_by_role("dialog")

                await login(2)
                await expect(page.get_by_label("Рекомендованная группа")).to_contain_text("261-001")
                for label, value in [
                    ("Рекомендованная группа", "1"),
                    ("Первая дисциплина", "1"),
                    ("Вторая дисциплина", "2"),
                ]:
                    await page.get_by_label(label, exact=True).select_option(value)
                await mutation(
                    "/participation",
                    lambda: page.get_by_role("button", name="Сохранить выбор").click(),
                )
                records = await (await page.request.get(base + "/api/testing?period_id=1")).json()
                identifier = next(
                    row["id"]
                    for row in records
                    if row["group_id"] == 1 and row["discipline_id"] == 1
                )
                await page.get_by_role("link", name="Выбор преподавателей", exact=True).click()
                await page.get_by_label("Проверка", exact=True).select_option(str(identifier))
                await page.get_by_label("Преподаватель", exact=True).select_option("3")
                await page.get_by_label("Дата / время (Москва)", exact=True).fill(
                    date.today().isoformat() + "T12:00"
                )
                await page.get_by_label("Аудитория", exact=True).fill("А-101")
                await mutation(
                    "/assignment",
                    lambda: page.get_by_role("button", name="Сохранить", exact=True).click(),
                )
                await login(3)
                await page.get_by_label("Проверка", exact=True).select_option(str(identifier))
                await mutation(
                    "/agreement",
                    lambda: page.get_by_role("button", name="Сохранить", exact=True).click(),
                )
                await page.get_by_role("link", name="Отчёты", exact=True).click()
                await page.get_by_role("button", name="Ведомость", exact=True).click()
                dialog = page.get_by_role("dialog")
                await expect(dialog.locator("tbody tr")).to_have_count(4)
                await dialog.get_by_label("Результат Тестовый студент 1", exact=True).fill("5")
                await dialog.get_by_label("Результат Тестовый студент 2", exact=True).fill("0")
                for student, status in [(3, "ABSENT"), (4, "NOT_ADMITTED")]:
                    await dialog.get_by_label(
                        f"Участие Тестовый студент {student}", exact=True
                    ).select_option(status)
                await mutation(
                    "/complete/",
                    lambda: dialog.get_by_role("button", name="Завершить ведомость").click(),
                )
                await dialog.get_by_role("button", name="Закрыть", exact=True).click()
                await expect(page.locator(".bool-value")).to_have_text(["Да"])
                dialog = await details()
                async with page.expect_download() as pending:
                    await dialog.get_by_role("button", name="Сформировать DOCX").click()
                report = output / "workflow-report.docx"
                await (await pending.value).save_as(report)
                await mutation(
                    "/report-workflow/testing/",
                    lambda: dialog.get_by_role("button", name="Создать карточку").click(),
                )
                dialog = await details()
                await mutation(
                    "/file", lambda: dialog.get_by_label("Файл отчёта").set_input_files(report)
                )
                await expect(page.locator(".table-container tbody")).to_contain_text(
                    "Требует проверки"
                )
                # Verify multipart uploads larger than Next.js's default 10 MiB proxy buffer.
                import io
                from zipfile import ZIP_STORED, ZipFile

                large = io.BytesIO()
                with (
                    ZipFile(report, "r") as source,
                    ZipFile(large, "w", compression=ZIP_STORED) as target,
                ):
                    for entry in source.namelist():
                        target.writestr(entry, source.read(entry))
                    target.writestr("padding.bin", b"0" * (11 * 1024 * 1024))
                report_rows = await (await page.request.get(base + "/api/reports/overview")).json()
                report_id = report_rows[0]["report_id"]
                uploaded = await page.request.post(
                    base + f"/api/report-workflow/{report_id}/file",
                    multipart={
                        "file": {
                            "name": "large-report.docx",
                            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "buffer": large.getvalue(),
                        }
                    },
                )
                assert uploaded.status == 200, await uploaded.text()
                await login(1)
                await page.get_by_role("link", name="Отчёты", exact=True).click()
                await expect(page.locator(".table-container tbody tr")).to_have_count(3)
                await choose("Дисциплина", "Базы данных")
                await expect(page.locator(".table-container tbody tr")).to_have_count(1)
                dialog = await details()
                await mutation(
                    "/review/electronic",
                    lambda: dialog.get_by_role("button", name="Одобрить", exact=True).click(),
                )
                await expect(page.locator(".table-container tbody")).to_contain_text("Всё сдано")
                policy = page.get_by_label("Принимать бумажные отчёты в выбранном семестре")
                await mutation("/report-policy", lambda: policy.check())
                await expect(page.locator(".table-container tbody")).to_contain_text("Не всё сдано")
                dialog = await details()
                await dialog.get_by_label("Версия", exact=True).select_option("paper")
                await mutation(
                    "/review/paper",
                    lambda: dialog.get_by_role("button", name="Одобрить", exact=True).click(),
                )
                await expect(page.locator(".table-container tbody")).to_contain_text("Всё сдано")
                await mutation("/report-policy", lambda: policy.uncheck())
                await expect(page.locator(".table-container tbody")).to_contain_text("Не требуется")
                await choose("Кафедра", "Кафедра информатики")
                await expect(page.locator(".table-container tbody tr")).to_have_count(3)
                await choose("Дисциплина", "Базы данных")
                await expect(page.locator(".table-container tbody tr")).to_have_count(1)
                await page.screenshot(path=str(output / "reports-lpr.png"), full_page=True)
                async with page.expect_download() as pending:
                    await page.get_by_role("button", name="Скачать сводный отчёт CSV").click()
                await (await pending.value).save_as(output / "summary.csv")
                await page.goto(base + "/lpr/list")
                await expect(
                    page.get_by_text("Предыдущие тестирования", exact=True)
                ).to_be_visible()
                choice = page.get_by_label(
                    "Рекомендовать группу 261-001: Осенний период", exact=True
                )
                await expect(choice).to_be_enabled()
                await choice.uncheck()
                await choose(
                    "Факультет / институт",
                    "Факультет информационных технологий",
                    "/groups/testing-overview?",
                    "faculty_id=1",
                )
                await expect(choice).not_to_be_checked()
                await mutation(
                    "/recommendations",
                    lambda: page.get_by_role("button", name="Сохранить рекомендации").click(),
                )
                await expect(choice).to_be_enabled()
                await expect(choice).not_to_be_checked()
                await page.get_by_role("button", name="Выбрать видимые", exact=True).click()
                await expect(choice).to_be_checked()
                await mutation(
                    "/recommendations",
                    lambda: page.get_by_role("button", name="Сохранить рекомендации").click(),
                )
                await expect(choice).to_be_enabled()
                await page.get_by_role("button", name="История", exact=True).first.click()
                history = page.get_by_role("dialog")
                await expect(history).to_contain_text("Рекомендация снята")
                await expect(history).to_contain_text("Рекомендована")
                await history.get_by_role("button", name="Закрыть", exact=True).click()
                await page.screenshot(path=str(output / "recommendations.png"), full_page=True)
                await page.goto(base + "/lpr/order")
                await page.get_by_role(
                    "button", name="Сформировать новый приказ", exact=True
                ).click()
                dialog = page.get_by_role("dialog")
                await dialog.get_by_label("Номер приказа", exact=True).fill("42-ОД")
                await mutation(
                    "/orders",
                    lambda: dialog.get_by_role(
                        "button", name="Сохранить черновик", exact=True
                    ).click(),
                )
                await page.get_by_role("button", name="Подробнее", exact=True).click()
                dialog = page.get_by_role("dialog")
                await dialog.get_by_label(
                    "Начальник отдела контроля образовательного процесса", exact=True
                ).fill("Иванов Иван Иванович")
                await dialog.get_by_label(
                    "Начальник центра по учебно-методической работе", exact=True
                ).fill("Петров Пётр Петрович")
                for label in [
                    "Дата приказа",
                    "Начало подготовительного этапа",
                    "Окончание подготовительного этапа",
                    "Начало тестирования",
                    "Окончание тестирования",
                    "Начало обработки результатов",
                    "Сводный отчёт по результатам проверки до",
                    "Начало анкетирования",
                    "Окончание анкетирования",
                    "Сводный отчёт по анкетированию до",
                    "Сдача электронных отчётов до",
                ]:
                    await dialog.get_by_label(label, exact=True).fill(date.today().isoformat())
                page.once("dialog", lambda modal: modal.accept())
                await mutation(
                    "/orders/",
                    lambda: dialog.get_by_role(
                        "button", name="Сформировать приказ", exact=True
                    ).click(),
                )
                async with page.expect_download() as pending:
                    await page.get_by_role("button", name="Скачать PDF", exact=True).click()
                await (await pending.value).save_as(output / "order.pdf")
                await page.screenshot(path=str(output / "orders.png"), full_page=True)
                for route in [
                    "/lpr/statistics",
                    "/lpr/order",
                    "/lpr/list",
                    "/lpr/report",
                    "/access-rights",
                    "/lpr/settings",
                ]:
                    await page.goto(base + route)
                    await expect(page.locator("main h1")).to_be_visible()
                    geometry = await page.evaluate(
                        "() => {const n=document.querySelector('.navbar-container').getBoundingClientRect(),m=document.querySelector('main').getBoundingClientRect();return {gap:m.left-n.right,top:m.top,border:parseFloat(getComputedStyle(document.querySelector('.page-header')).borderBottomWidth)}}"
                    )
                    assert geometry == {"gap": 8, "top": 8, "border": 8}, (route, geometry)
                    assert await page.get_by_text("Рабочие процессы", exact=True).count() == 0
                await login(4)
                await expect(page.locator(".table-container tbody tr")).to_have_count(2)
                await expect(page.locator("main")).not_to_contain_text("Чужая группа")
                assert await policy.count() == 0
                assert (
                    await (
                        await page.request.get(base + "/api/reports/overview?faculty_id=3")
                    ).json()
                    == []
                )
                assert (
                    await page.request.patch(
                        base + "/api/periods/1/report-policy", data={"paper_reports_required": True}
                    )
                ).status == 403
                await page.screenshot(path=str(output / "reports-dean.png"), full_page=True)
                await page.locator(".navbar-theme-toggle").click()
                await page.screenshot(path=str(output / "reports-dark.png"), full_page=True)
                await page.set_viewport_size({"width": 390, "height": 844})
                await expect(page.locator(".navbar-container")).to_have_css("width", "68px")
                await page.screenshot(path=str(output / "reports-mobile.png"), full_page=True)
                assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                print(
                    "Next.js workflow passed: recommendations matrix/history/bulk selection, orders/drafts/PDF, role pages, 8px gaps, dean scope, optional paper, participation, results, upload, DOCX/CSV; no JS errors."
                )
                await browser.close()
        except Exception as exc:
            print("Browser failure:", repr(exc))
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
            log.close()
            server.should_exit = True
            await task
            await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
