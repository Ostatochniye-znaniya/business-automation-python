from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import TestingPeriodStatus


class TestingPeriodBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    academic_year: str = Field(min_length=1, max_length=9)
    semester: int = Field(ge=1, le=2)
    start_date: date
    end_date: date
    status: TestingPeriodStatus = TestingPeriodStatus.DRAFT


class TestingPeriodCreate(TestingPeriodBase):
    @model_validator(mode="after")
    def validate_dates(self) -> "TestingPeriodCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class TestingPeriodRead(TestingPeriodBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
