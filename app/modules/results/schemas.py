from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ParticipationStatus


class TestResultCreate(BaseModel):
    knowledge_test_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    intermediate_result: float | None = None
    testing_result: float | None = None
    participation_status: ParticipationStatus


class TestResultRead(TestResultCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
