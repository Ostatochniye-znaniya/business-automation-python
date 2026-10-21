import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.base import register_models
from app.db.demo import seed_demo_data
from app.db.session import engine, session_factory


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        if get_settings().DEMO_DATA:
            async with session_factory() as session:
                await seed_demo_data(session)
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    register_models()
    application = FastAPI(
        title=settings.APP_NAME, version="0.1.0", debug=settings.DEBUG, lifespan=lifespan
    )
    register_exception_handlers(application)

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        started = perf_counter()
        response = await call_next(request)
        logging.getLogger("app.http").info(
            "%s %s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response

    @application.get("/app-config.js", include_in_schema=False)
    async def frontend_config() -> Response:
        return Response(
            "window.APP_CONFIG = "
            + json.dumps({"apiBase": settings.API_PREFIX, "demoData": settings.DEMO_DATA})
            + ";",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    application.include_router(api_router, prefix=settings.API_PREFIX)

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Статика монтируется только по флагу: mount("/") перехватывает все пути,
    # добавленные после create_app(), и ломает регистрацию маршрутов в тестах.
    if settings.SERVE_FRONTEND:
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
        application.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return application


app = create_app()
