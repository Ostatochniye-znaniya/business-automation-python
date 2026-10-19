from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int | None] = mapped_column(ForeignKey("testing_periods.id"))
    title: Mapped[str] = mapped_column(String(500))
    year: Mapped[str] = mapped_column(String(9))
    semester: Mapped[str] = mapped_column(String(16))
    date: Mapped[str] = mapped_column(String(10))
    draft: Mapped[bool] = mapped_column(default=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
