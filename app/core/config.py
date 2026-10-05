from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    APP_NAME: str = "Остаточные знания — Московский Политех"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    DATABASE_URL: str = "mysql+asyncmy://knowledge:knowledge@localhost:3306/knowledge_app"
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
