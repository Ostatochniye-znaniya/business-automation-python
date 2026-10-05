from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[int] = mapped_column(ForeignKey("study_groups.id"))
