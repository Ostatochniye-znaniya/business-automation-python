from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeTestCreate(BaseModel):
    period_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    discipline_id: int = Field(gt=0)
    teacher_id: int | None = Field(default=None, gt=0)
    scheduled_at: datetime | None = None


class KnowledgeTestRead(KnowledgeTestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ScheduleUpdate(BaseModel):
    scheduled_at: datetime | None = None
