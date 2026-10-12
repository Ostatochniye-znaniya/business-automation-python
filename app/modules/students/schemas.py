from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    group_id: int = Field(gt=0)


class StudentUpdate(StudentCreate):
    pass


class StudentRead(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
