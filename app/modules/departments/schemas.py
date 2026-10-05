from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DepartmentType


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=64)
    parent_id: int | None = Field(default=None, gt=0)
    type: DepartmentType


class DepartmentRead(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
