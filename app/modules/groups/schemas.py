from pydantic import BaseModel, ConfigDict, Field


class StudyGroupCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    study_program_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)


class StudyGroupRead(StudyGroupCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DashboardStatistics(BaseModel):
    """Group counts for a dashboard department row."""

    required: int | None = None
    actual: int | None = None


class StudyProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str | None
    faculty_id: int
