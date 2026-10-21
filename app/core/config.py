from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    APP_NAME: str = "Остаточные знания — Московский Политех"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    DATABASE_URL: str = "mysql+asyncmy://knowledge:knowledge@localhost:3306/knowledge_app"
    LOG_LEVEL: str = "INFO"
    SERVE_FRONTEND: bool = False
    DEMO_DATA: bool = False
    DEV_USER_ID: int | None = Field(default=None, gt=0)

    @field_validator("API_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value):
            raise ValueError("API_PREFIX must be an absolute path without a trailing slash")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported LOG_LEVEL")
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        url = make_url(value)
        if url.drivername != "mysql+asyncmy" or not url.host or not url.database:
            raise ValueError("DATABASE_URL must use mysql+asyncmy with a host and database")
        return value

    @model_validator(mode="after")
    def validate_debug(self) -> "Settings":
        if self.APP_ENV == "production" and self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")
        if self.DEMO_DATA and self.APP_ENV not in {"development", "test"}:
            raise ValueError("DEMO_DATA is only supported in development and test environments")
        if self.DEV_USER_ID is not None and self.APP_ENV not in {"development", "test"}:
            raise ValueError("DEV_USER_ID is only supported in development and test environments")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
