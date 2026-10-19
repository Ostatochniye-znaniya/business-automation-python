"""Explicit imports: parse and validate the whole document before persistence."""

import csv
import io
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticError
from sqlalchemy import select

from app.core.enums import UserRole
from app.core.exceptions import ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.departments.models import Department
from app.modules.users.models import ImportLog, User


class EmployeeRecord(BaseModel):
    external_id: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    position: str | None = Field(default=None, max_length=255)
    department_id: int | None = Field(default=None, gt=0)


def read_employees(filename, content):
    if len(content) > 5 * 1024 * 1024:
        raise ValidationError("Максимальный размер импорта — 5 МБ")
    if filename.lower().endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("Используйте CSV в UTF-8") from exc
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
        rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    elif filename.lower().endswith(".xlsx"):
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            values = iter(workbook.active.values)
            headers = next(values)
            rows = [dict(zip(headers, row, strict=False)) for row in values if any(row)]
        finally:
            workbook.close()
    else:
        raise ValidationError("Поддерживаются CSV и XLSX")
    if not rows or len(rows) > 10000:
        raise ValidationError("Импорт должен содержать от 1 до 10000 сотрудников")
    try:
        records = [
            EmployeeRecord.model_validate(
                {key: value for key, value in row.items() if value not in ("", None)}
            )
            for row in rows
        ]
    except PydanticError as exc:
        raise ValidationError(
            "Проверьте поля external_id, full_name, email, position, department_id"
        ) from exc
    if len({record.external_id for record in records}) != len(records):
        raise ValidationError("В файле повторяются табельные номера")
    return records


class ImportService:
    def __init__(self, session):
        self.session = session

    async def employees(self, filename, content, actor, deactivate_missing=False):
        require_role(actor, MANAGERS)
        log = ImportLog(
            started_at=datetime.now(UTC).replace(tzinfo=None), status="RUNNING", errors=[]
        )
        started = log.started_at
        self.session.add(log)
        await self.session.flush()
        try:
            records = read_employees(filename, content)
            department_ids = {record.department_id for record in records if record.department_id}
            existing = set(
                (
                    await self.session.scalars(
                        select(Department.id).where(Department.id.in_(department_ids))
                    )
                ).all()
            )
            if existing != department_ids:
                raise ValidationError("Файл содержит неизвестные подразделения")
            users = {
                user.external_id: user
                for user in (
                    await self.session.scalars(select(User).where(User.external_id.is_not(None)))
                ).all()
            }
            for record in records:
                user = users.get(record.external_id)
                if user is None:
                    user = User(role=UserRole.GUEST, is_active=True)
                    self.session.add(user)
                for key, value in record.model_dump().items():
                    setattr(user, key, value)
            if deactivate_missing:
                require_role(actor, {UserRole.ADMIN})
                imported = {record.external_id for record in records}
                if actor.external_id not in imported:
                    raise ValidationError("Полный импорт должен содержать текущего администратора")
                for external_id, user in users.items():
                    if external_id not in imported:
                        user.is_active = False
            log.status = "SUCCESS"
            log.records_processed = len(records)
            log.finished_at = datetime.now(UTC).replace(tzinfo=None)
            audit(self.session, actor, "employees.import", log.id)
            await self.session.commit()
            return log
        except Exception as exc:
            await self.session.rollback()
            failure = ImportLog(
                started_at=started,
                finished_at=datetime.now(UTC).replace(tzinfo=None),
                status="FAILED",
                records_processed=0,
                errors=[str(exc)[:500]],
            )
            self.session.add(failure)
            await self.session.commit()
            if isinstance(exc, ValidationError):
                raise
            raise ValidationError("Не удалось прочитать импортируемый файл") from exc
