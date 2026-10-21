from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import UserRole
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.GUEST)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    position: Mapped[str | None] = mapped_column(String(255))


class AccessRequest(Base):
    __tablename__ = "access_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    requested_role: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(DateTime)
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[int | None] = mapped_column()
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ImportLog(Base):
    __tablename__ = "import_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16))
    records_processed: Mapped[int] = mapped_column(default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)


class DevSession(Base):
    __tablename__ = "dev_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
