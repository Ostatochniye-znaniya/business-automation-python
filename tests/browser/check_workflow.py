"""Real HTTP and browser walkthrough using disposable SQLite data.

Run: python tests/browser/check_workflow.py --output <directory>
Requires Playwright and Microsoft Edge (or Playwright Chromium).
"""

import argparse
import asyncio
import os
import socket
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
    os.environ.update(SERVE_FRONTEND="true", APP_ENV="test", DEMO_DATA="false")
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
                    Student(id=1, full_name="Тестовый студент", group_id=1),
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
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        task = asyncio.create_task(server.serve())
        for _ in range(100):
            if server.started:
                break
            await asyncio.sleep(0.05)
        output.mkdir(parents=True, exist_ok=True)
        try:
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
                base = f"http://127.0.0.1:{port}"

                async def login(user_id):
                    await page.goto(base + "/pages/login.html")
                    await page.locator("#login-user").select_option(str(user_id))
                    await page.locator("#login-form button").click()
                    await page.wait_for_url("**/pages/workbench.html")
                    await expect(page.locator("#status")).to_have_text("Выберите действие.")

                async def mutation(path, click):
                    async with page.expect_response(
                        lambda response: (
                            path in response.url and response.request.method in {"POST", "PUT"}
                        )
                    ) as waiting:
                        await click()
                    response = await waiting.value
                    assert response.ok, await response.text()
                    return await response.json()

                await login(2)
                await page.locator("#participation [name=group_id]").select_option("1")
                await page.locator("#participation [name=discipline1]").select_option("1")
                await page.locator("#participation [name=discipline2]").select_option("2")
                await mutation(
                    "/workflow/participation", lambda: page.locator("#participation button").click()
                )
                await expect(page.locator("#test-rows tr")).to_have_count(2)
                response = await page.request.get(base + "/api/testing?period_id=1")
                test_id = (await response.json())[0]["id"]
                await page.locator("#assignment [name=test_id]").select_option(str(test_id))
                await page.locator("#assignment [name=teacher_id]").select_option("3")
                await page.locator("#assignment [name=scheduled_at]").fill(
                    date.today().isoformat() + "T12:00"
                )
                await page.locator("#assignment [name=room]").fill("А-101")
                await mutation("/assignment", lambda: page.locator("#assignment button").click())

                await login(3)
                await page.locator("[data-tab=planning]").click()
                await page.locator("#agreement [name=test_id]").select_option(str(test_id))
                await mutation("/agreement", lambda: page.locator("#agreement button").click())
                await page.locator("[data-tab=results]").click()
                await page.locator("#result-test").select_option(str(test_id))
                await page.locator("#load-roster").click()
                await expect(page.locator("#result-rows tr")).to_have_count(1)
                await page.locator("#result-rows input").nth(0).fill("4")
                await page.locator("#result-rows input").nth(1).fill("5")
                await mutation("/results", lambda: page.locator("#result-rows button").click())
                await mutation("/results/complete", lambda: page.locator("#complete").click())
                async with page.expect_download() as pending:
                    await page.locator("#report-document").click()
                downloaded = await pending.value
                report_path = output / "workflow-report.docx"
                await downloaded.save_as(report_path)
                await mutation(
                    "/report-workflow/testing", lambda: page.locator("#create-report").click()
                )
                await expect(page.locator("#report-state")).to_contain_text("Черновик")
                await page.locator("#upload [name=file]").set_input_files(report_path)
                await mutation("/file", lambda: page.locator("#upload button").click())
                await expect(page.locator("#report-state")).to_contain_text("На проверке")

                await login(1)
                await page.locator("[data-tab=review]").click()
                await page.locator("#load-reviews").click()
                await expect(page.locator("#review-rows tr")).to_have_count(1)
                await page.locator("#review-report").select_option(index=1)
                await mutation(
                    "/review/electronic", lambda: page.locator("#review-form button").click()
                )
                await page.locator("#review-report").select_option(index=1)
                await page.locator("#review-form [name=version]").select_option("paper")
                await mutation("/review/paper", lambda: page.locator("#review-form button").click())
                await expect(page.locator("#review-rows")).to_contain_text("Всё сдано")
                await page.screenshot(path=str(output / "workflow-review.png"), full_page=True)
                await page.locator("[data-tab=planning]").click()
                async with page.expect_download() as pending:
                    await page.locator("#schedule").click()
                await (await pending.value).save_as(output / "workflow-schedule.pdf")
                await page.set_viewport_size({"width": 390, "height": 844})
                await page.screenshot(path=str(output / "workflow-mobile.png"), full_page=True)
                assert not errors, errors
                print(
                    "Browser workflow passed: selection, assignment, agreement, results, upload, review, DOCX, PDF; no JS errors."
                )
                await browser.close()
        finally:
            server.should_exit = True
            await task
            await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
