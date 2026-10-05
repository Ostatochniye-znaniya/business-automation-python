from app.core.config import Settings


def test_settings_environment(monkeypatch):
    monkeypatch.setenv("API_PREFIX", "/custom")
    assert Settings(_env_file=None).API_PREFIX == "/custom"


def test_settings_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=test\nLOG_LEVEL=WARNING\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    assert settings.APP_ENV == "test"
