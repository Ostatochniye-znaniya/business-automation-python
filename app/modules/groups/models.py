from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyGroup(Base):
    __tablename__ = "study_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
