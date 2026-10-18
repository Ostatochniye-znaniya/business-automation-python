from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyGroup(Base):
    __tablename__ = "study_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    study_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_programs.id"), index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))


class StudyProgram(Base):
    __tablename__ = "study_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(32))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)


class GroupPeriod(Base):
    """Groups enrolled in a period, including groups without any tests yet."""

    __tablename__ = "group_periods"
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"), primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"), primary_key=True)
