import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def application():
    return create_app()


@pytest.fixture
async def client(application):
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        yield client
