async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_swagger_and_openapi(client):
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_application_error_translation(client, application):
    from app.core.exceptions import NotFoundError
    from app.modules.users.dependencies import require_staff
    from app.modules.users.router import get_service

    class MissingUserService:
        async def get_by_id(self, entity_id: int):
            raise NotFoundError("User not found")

    application.dependency_overrides[get_service] = lambda: MissingUserService()
    application.dependency_overrides[require_staff] = lambda: None
    try:
        response = await client.get("/api/users/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}
    finally:
        application.dependency_overrides.clear()
