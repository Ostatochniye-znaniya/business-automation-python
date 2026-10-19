from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    year: str = Field(pattern=r"^\d{4}(/\d{4})?$")
    semester: Literal["Весна", "Осень"]
    date: date
    draft: bool = True
    period_id: int | None = Field(default=None, gt=0)
    details: dict[str, str] = Field(default_factory=dict, max_length=30)


class OrderRead(OrderCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
