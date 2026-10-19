from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AuthCallbackRequest(BaseModel):
    access: str = Field(..., description="Access token from Polytech Admin API")
    refresh: str = Field(..., description="Refresh token from Polytech Admin API")


class AuthRefreshRequest(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: str | None = None


class PolytechLoginRequest(BaseModel):
    login: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class PolytechVerifyRequest(BaseModel):
    login: str = Field(..., min_length=1)
    code: Any = Field(..., description="Verification code sent via SMS/Email")


class PolytechTokenResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str


class UserMeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    external_id: str | None = None
    name: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    surname: str | None = None
    patronymic: str | None = None
    email: str | None = None
    mail_box: str | None = None
    status_id: int | None = None
    status: str | None = None
    faculty_id: int | None = None
    faculty: str | None = None
    role: str | None = None
    roles: list[str] = Field(default_factory=list)
    access_token: str | None = None
    refresh_token: str | None = None
