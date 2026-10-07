from fastapi import FastAPI


def test_application_created(application):
    assert isinstance(application, FastAPI)


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_swagger_and_openapi(client):
    assert (await client.get("/docs")).status_code == 200
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert {
        "/health",
        "/api/periods",
        "/api/periods/{period_id}",
        "/api/students",
        "/api/students/{student_id}",
    } <= paths
