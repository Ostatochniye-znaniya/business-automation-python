from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecommendationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: int = Field(gt=0)
    period_id: int = Field(gt=0)
    recommended: bool
    expected_version: int = Field(ge=0)


class RecommendationSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    changes: list[RecommendationChange] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def unique_pairs(self):
        pairs = {(change.group_id, change.period_id) for change in self.changes}
        if len(pairs) != len(self.changes):
            raise ValueError("Одна группа и период не должны повторяться в запросе")
        return self


class RecommendationRead(BaseModel):
    id: int
    group_id: int
    period_id: int
    recommended: bool
    version: int
    changed_by_id: int
    changed_by_name: str
    changed_at: datetime

    @field_validator("changed_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class RecommendationHistoryRead(RecommendationRead):
    period_name: str
