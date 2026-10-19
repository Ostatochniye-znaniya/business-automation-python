from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import KnowledgeTestStatus


class KnowledgeTestCreate(BaseModel):
    period_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    discipline_id: int = Field(gt=0)
    teacher_id: int | None = Field(default=None, gt=0)
    status: KnowledgeTestStatus = KnowledgeTestStatus.PLANNED
    scheduled_at: datetime | None = None


class KnowledgeTestRead(KnowledgeTestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agreement_status: str = "PROPOSED"
    agreement_comment: str | None = None
    room: str | None = None


class ScheduleUpdate(BaseModel):
    scheduled_at: datetime | None = None


class ParticipationSave(BaseModel):
    group_id: int = Field(gt=0)
    period_id: int = Field(gt=0)
    participates: bool
    discipline_ids: list[int] = Field(default_factory=list, max_length=2)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_disciplines(self):
        if self.participates and (
            len(self.discipline_ids) != 2 or len(set(self.discipline_ids)) != 2
        ):
            raise ValueError("Для участвующей группы выберите две различные дисциплины")
        if not self.participates and self.discipline_ids:
            raise ValueError("Для неучаствующей группы дисциплины не выбираются")
        return self


class AssignmentSave(BaseModel):
    teacher_id: int = Field(gt=0)
    scheduled_at: datetime
    room: str = Field(min_length=1, max_length=100)


class AgreementSave(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=2000)
