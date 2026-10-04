from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ApplicationError,
    ConflictError,
    FeatureNotImplementedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    codes = {
        NotFoundError: 404,
        ConflictError: 409,
        ForbiddenError: 403,
        ValidationError: 422,
        FeatureNotImplementedError: 501,
    }
    return JSONResponse(status_code=codes.get(type(exc), 400), content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
