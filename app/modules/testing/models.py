from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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


class GroupParticipation(Base):
    __tablename__ = "group_participation"
    __table_args__ = (UniqueConstraint("group_id", "period_id", name="uq_participation"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"))
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"))
    participates: Mapped[bool] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
