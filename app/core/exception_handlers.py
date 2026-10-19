import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    ApplicationError,
    ConflictError,
    FeatureNotImplementedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    codes = {
        NotFoundError: 404,
        ConflictError: 409,
        ForbiddenError: 403,
        ValidationError: 422,
        FeatureNotImplementedError: 501,
    }
    status = next((code for kind, code in codes.items() if isinstance(exc, kind)), 400)
    logger.warning("Application error: %s %s status=%s", request.method, request.url.path, status)
    return JSONResponse(status_code=status, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Database constraint conflict: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=409,
        content={"detail": "Запись уже существует или используется в связанных данных"},
    )
