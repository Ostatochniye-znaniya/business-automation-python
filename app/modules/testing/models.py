from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import KnowledgeTestStatus
from app.db.base import Base


class KnowledgeTest(Base):
    __tablename__ = "knowledge_tests"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"))
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[KnowledgeTestStatus] = mapped_column(
        Enum(KnowledgeTestStatus), default=KnowledgeTestStatus.PLANNED
    )
    scheduled_at: Mapped[datetime | None] = mapped_column()
    agreement_status: Mapped[str] = mapped_column(String(16), default="PROPOSED")
    agreement_comment: Mapped[str | None] = mapped_column(Text)
    room: Mapped[str | None] = mapped_column(String(100))

    assignments: Mapped[list["TestAssignment"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="TestAssignment.id"
    )


class TestAssignment(Base):
    __tablename__ = "test_assignments"
    __table_args__ = (UniqueConstraint("knowledge_test_id", "teacher_id", name="uq_test_teacher"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_test_id: Mapped[int] = mapped_column(ForeignKey("knowledge_tests.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    scheduled_at: Mapped[datetime | None] = mapped_column()
    agreement_status: Mapped[str] = mapped_column(String(16), default="PROPOSED")
    agreement_comment: Mapped[str | None] = mapped_column(Text)


class GroupParticipation(Base):
    __tablename__ = "group_participation"
    __table_args__ = (UniqueConstraint("group_id", "period_id", name="uq_participation"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"))
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"))
    participates: Mapped[bool] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
