from html.parser import HTMLParser
from urllib.parse import urljoin

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = "src" if tag in {"script", "img"} else "href" if tag == "link" else None
        if key and attrs.get(key):
            self.paths.append(attrs[key])


async def test_all_sections_and_their_assets_are_served(monkeypatch):
    monkeypatch.setenv("SERVE_FRONTEND", "true")
    get_settings.cache_clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            for path in (
                "/",
                "/pages/orders.html",
                "/pages/groups.html",
                "/pages/reports.html",
                "/pages/access.html",
                "/pages/options.html",
                "/pages/optionsDate.html",
                "/pages/workbench.html",
                "/pages/login.html",
            ):
                response = await client.get(path)
                assert response.status_code == 200, path
                parser = Assets()
                parser.feed(response.text)
                for asset in parser.paths:
                    assert (await client.get(urljoin(path, asset))).status_code == 200, asset
                assert "/js/theme.js" in response.text
                assert 'id="sidebar"' in response.text
    finally:
        get_settings.cache_clear()
