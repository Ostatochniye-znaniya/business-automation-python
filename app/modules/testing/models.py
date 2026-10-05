from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeTest(Base):
    __tablename__ = "knowledge_tests"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"))
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    scheduled_at: Mapped[datetime | None] = mapped_column()
