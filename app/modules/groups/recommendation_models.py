from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GroupRecommendation(Base):
    __tablename__ = "group_recommendations"
    __table_args__ = (
        UniqueConstraint("group_id", "period_id", name="uq_recommendation_group_period"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"), index=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("testing_periods.id"), index=True)
    recommended: Mapped[bool] = mapped_column()
    version: Mapped[int] = mapped_column()
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime())


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("group_recommendations.id"), index=True
    )
    recommended: Mapped[bool] = mapped_column()
    version: Mapped[int] = mapped_column()
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime())
