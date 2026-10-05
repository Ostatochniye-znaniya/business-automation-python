from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.base import register_models
from app.db.session import engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    register_models()
    application = FastAPI(
        title=settings.APP_NAME, version="0.1.0", debug=settings.DEBUG, lifespan=lifespan
    )
    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.API_PREFIX)

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
