from pydantic import BaseModel, ConfigDict, Field


class DisciplineCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    department_id: int | None = Field(default=None, gt=0)


class DisciplineRead(DisciplineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
