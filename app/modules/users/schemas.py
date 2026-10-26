from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole


class UserCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    role: UserRole = UserRole.GUEST
    department_id: int | None = Field(default=None, gt=0)
    position: str | None = Field(default=None, max_length=255)


class UserRead(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AccessRequestCreate(BaseModel):
    requested_role: UserRole
    reason: str = Field(min_length=1, max_length=2000)


class AccessDecision(BaseModel):
    approved: bool


class DevelopmentLogin(BaseModel):
    user_id: int = Field(gt=0)
