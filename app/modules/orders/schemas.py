from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    number: str | None = Field(default=None, max_length=50)
    year: str = Field(pattern=r"^\d{4}(/\d{4})?$")
    semester: Literal["Весна", "Осень"]
    date: date
    draft: bool = True
    period_id: int | None = Field(default=None, gt=0)
    details: dict[str, str] = Field(default_factory=dict, max_length=30)


class OrderRead(OrderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class OrderPublication(BaseModel):
    """Fields required for the printable order, matching the C# develop contract."""

    model_config = ConfigDict(str_strip_whitespace=True)
    bossControl: str = Field(min_length=1, max_length=200)
    bossMethod: str = Field(min_length=1, max_length=200)
    checkSummaryDate: date
    surveySummaryDate: date
    electronicReportDeadline: date
    paperReportDeadline: date | None = None
    testingStartDate: date
    testingEndDate: date
    surveyStartDate: date
    surveyEndDate: date
    preparationStartDate: date
    preparationEndDate: date
    resultsProcessingStartDate: date
