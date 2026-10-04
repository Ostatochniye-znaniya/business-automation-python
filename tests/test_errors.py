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
