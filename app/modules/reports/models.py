from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_test_id: Mapped[int] = mapped_column(ForeignKey("knowledge_tests.id"), unique=True)
    electronic_file_key: Mapped[str | None] = mapped_column(String(500))
    electronic_status: Mapped[str | None] = mapped_column(String(32))
    electronic_comment: Mapped[str | None] = mapped_column(Text)
    paper_status: Mapped[str | None] = mapped_column(String(32))
    paper_comment: Mapped[str | None] = mapped_column(Text)
    final_status: Mapped[str | None] = mapped_column(String(32))
    previous_teacher_name: Mapped[str | None] = mapped_column(String(255))


class FacultySchedule(Base):
    __tablename__ = "faculty_schedules"
    __table_args__ = (UniqueConstraint("faculty_id", "period_id", name="uq_faculty_schedule"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"))
    file_key: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED")
    comment: Mapped[str | None] = mapped_column(Text)
