import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def application(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("SERVE_FRONTEND", "false")
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()
    yield create_app()
    get_settings.cache_clear()


@pytest.fixture
async def client(application):
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def db_session(application):
    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.base import Base
    from app.db.dependencies import get_db_session

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:

        async def override_session():
            yield session

        application.dependency_overrides[get_db_session] = override_session
        yield session
        application.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()
