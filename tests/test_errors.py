import pytest

from app.core.exceptions import (
    ApplicationError,
    ConflictError,
    FeatureNotImplementedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


@pytest.mark.parametrize(
    "error, status",
    [
        (ApplicationError, 400),
        (NotFoundError, 404),
        (ConflictError, 409),
        (ForbiddenError, 403),
        (ValidationError, 422),
        (FeatureNotImplementedError, 501),
    ],
)
async def test_error_response(client, application, error, status):
    @application.get("/test-error")
    async def fail():
        raise error("Test error")

    response = await client.get("/test-error")
    assert response.status_code == status
    assert response.json() == {"detail": "Test error"}


async def test_unexpected_error_is_logged_without_exposing_details(application, caplog):
    import logging

    from httpx import ASGITransport, AsyncClient

    @application.get("/test-unexpected")
    async def fail():
        raise RuntimeError("sensitive internal detail")

    with caplog.at_level(logging.ERROR):
        async with AsyncClient(
            transport=ASGITransport(app=application, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/test-unexpected")
    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}
    assert "Unhandled error: GET /test-unexpected" in caplog.text
    assert "sensitive internal detail" in caplog.text


async def test_application_error_subclass(client, application):
    class MissingItem(NotFoundError):
        pass

    @application.get("/test-subclass")
    async def fail():
        raise MissingItem("Missing")

    assert (await client.get("/test-subclass")).status_code == 404
