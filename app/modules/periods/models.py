from datetime import date

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import TestingPeriodStatus
from app.db.base import Base


class TestingPeriod(Base):
    __tablename__ = "testing_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    academic_year: Mapped[str] = mapped_column(String(9))
    semester: Mapped[int] = mapped_column()
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date] = mapped_column()
    status: Mapped[TestingPeriodStatus] = mapped_column(
        Enum(TestingPeriodStatus), default=TestingPeriodStatus.DRAFT
    )
