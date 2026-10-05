from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DepartmentType
from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(64))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    type: Mapped[DepartmentType] = mapped_column(Enum(DepartmentType))
