def test_create_app_registers_migration_extension(app):
    assert "migrate" in app.extensions


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "OK"}
