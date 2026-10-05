from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole


class UserCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    role: UserRole = UserRole.GUEST


class UserRead(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
