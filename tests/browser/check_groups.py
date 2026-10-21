"""Run with: python tests/browser/check_groups.py (requires playwright + Chromium)."""

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


async def check():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        calls = []
        fail_groups = False
        slow_request = asyncio.Event()
        release_request = asyncio.Event()
        delay_next = False
        catalogs = {
            "/api/departments": [
                {"id": 1, "name": "ФИТ", "type": "FACULTY"},
                {"id": 2, "name": "Институт", "type": "INSTITUTE"},
            ],
            "/api/programs": [
                {"id": 1, "name": "Информатика", "code": "09.03.01", "faculty_id": 1},
                {"id": 2, "name": "Экономика", "code": None, "faculty_id": 2},
            ],
            "/api/periods": [
                {"id": 1, "academic_year": "2025/2026", "semester": 1},
                {"id": 2, "academic_year": "2026/2027", "semester": 2},
            ],
        }

        async def route_request(route):
            nonlocal delay_next
            url = urlparse(route.request.url)
            query = parse_qs(url.query)
            if url.path == "/api/groups/testing-overview":
                calls.append(query)
                if fail_groups:
                    await route.fulfill(status=500, json={"detail": "Ошибка БД"})
                    return
                payload = [
                    {
                        "id": 1,
                        "name": "241-001",
                        "study_program_id": 1,
                        "admission_year": 2024,
                        "testings": [
                            {
                                "id": 1,
                                "period_id": 1,
                                "discipline_name": "Базы данных",
                                "status": "COMPLETED",
                                "scheduled_at": None,
                            }
                        ],
                    }
                ]
                if query.get("faculty_id") == ["2"]:
                    payload = [{"id": 2, "name": "241-002", "study_program_id": 2}]
                if query.get("academic_year") == ["2026/2027"] and query.get("faculty_id") == ["1"]:
                    payload = []
                if delay_next:
                    delay_next = False
                    slow_request.set()
                    await release_request.wait()
                await route.fulfill(json=payload)
            elif url.path in catalogs:
                await route.fulfill(json=catalogs[url.path])
            elif url.path == "/app-config.js":
                await route.fulfill(
                    body='window.APP_CONFIG = {apiBase: "/api"};',
                    content_type="application/javascript",
                )
            else:
                path = ROOT / "frontend" / url.path.lstrip("/")
                if path.is_file():
                    await route.fulfill(path=path)
                else:
                    await route.fulfill(status=404, body="Not found")

        await page.route("http://knowledge.test/**", route_request)
        await page.goto("http://knowledge.test/pages/groups.html")
        await expect(page.locator("#groups-status")).to_have_text("Найдено групп: 1")
        await page.select_option("#faculty", "1")
        await page.select_option("#program", "1")
        await expect(page.locator("#groups-body")).to_contain_text("241-001")
        await page.select_option("#academic-year", "2025/2026")
        await page.select_option("#semester", "1")
        await expect(page.locator("#groups-status")).to_have_text("Найдено групп: 1")
        assert calls[-1]["study_program_id"] == ["1"]
        assert calls[-1]["academic_year"] == ["2025/2026"]
        assert calls[-1]["semester"] == ["1"]
        await page.select_option("#faculty", "2")
        await expect(page.locator("#program")).to_have_value("")
        await expect(page.locator("#program option")).to_have_count(2)
        await expect(page.locator("#groups-body")).to_contain_text("241-002")
        await page.select_option("#academic-year", "2026/2027")
        await expect(page.locator("#semester")).to_have_value("")
        # A slow earlier request must never overwrite the latest selection.
        delay_next = True
        await page.select_option("#faculty", "1")
        await slow_request.wait()
        await page.select_option("#faculty", "2")
        await expect(page.locator("#groups-body")).to_contain_text("241-002")
        release_request.set()
        await page.wait_for_load_state("networkidle")
        await expect(page.locator("#groups-body")).to_contain_text("241-002")
        fail_groups = True
        await page.select_option("#faculty", "1")
        await expect(page.locator("#groups-status")).to_contain_text("Ошибка БД")
        await expect(page.locator("#groups-body tr")).to_have_count(0)
        fail_groups = False
        await page.click("#retry")
        await expect(page.locator("#groups-status")).to_contain_text("не найдены")
        # Values from the server are text, never executable HTML.
        catalogs["/api/programs"][0]["name"] = '<img src=x onerror="alert(1)">'
        await page.reload()
        await expect(page.locator("#groups-body th")).to_have_attribute(
            "title", '<img src=x onerror="alert(1)">'
        )
        assert await page.locator("#groups-body img").count() == 0
        await expect(page.locator("#groups-head")).to_contain_text("Предыдущие тестирования")
        await expect(page.locator("#groups-body .testing-mark--completed")).to_have_count(1)
        assert await page.locator("#groups-body td").first.text_content() != "—"
        # Pagination is also exercised by the shared helper.
        await page.route(
            "**/api/pagination-check?*",
            lambda route: route.fulfill(
                json=(list(range(100)) if "offset=0&" in route.request.url else [100])
            ),
        )
        assert (
            await page.evaluate("async () => (await apiGetAll('/pagination-check')).length") == 101
        )
        await page.screenshot(path="/private/tmp/knowledge-groups.png", full_page=True)
        await page.locator("#theme-toggle").check()
        await expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        await page.screenshot(path="/private/tmp/knowledge-groups-dark.png", full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await page.screenshot(path="/private/tmp/knowledge-groups-mobile.png", full_page=True)
        assert not errors, errors
        await browser.close()
        print("Group filter browser checks passed")


if __name__ == "__main__":
    asyncio.run(check())
