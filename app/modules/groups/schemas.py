from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import KnowledgeTestStatus
from app.modules.groups.recommendation_schemas import RecommendationRead


class StudyGroupCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    admission_year: int | None = Field(default=None, ge=1900, le=3000)
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


class GroupTestingSummary(BaseModel):
    id: int
    period_id: int
    discipline_name: str
    scheduled_at: datetime | None
    status: KnowledgeTestStatus


class GroupTestingOverview(StudyGroupRead):
    testings: list[GroupTestingSummary]
    recommendations: list[RecommendationRead]
    enrolled_period_ids: list[int]
