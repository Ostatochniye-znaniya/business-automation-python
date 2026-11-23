"""Submission and faculty-scoped review of semester schedules."""

from pathlib import Path

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.enums import DepartmentType, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.departments.models import Department
from app.modules.periods.service import PeriodService
from app.modules.reports.files import save_file, storage_path
from app.modules.reports.models import FacultySchedule


class FacultyScheduleService:
    def __init__(self, session):
        self.session = session

    async def authorize(self, faculty_id, actor, *, write=False, review=False):
        roles = (
            {UserRole.DEPARTMENT_HEAD}
            if review
            else (
                {UserRole.DEPARTMENT_RESPONSIBLE}
                if write
                else {UserRole.DEPARTMENT_RESPONSIBLE, UserRole.DEPARTMENT_HEAD}
            )
        )
        require_role(actor, roles | MANAGERS)
        faculty = await self.session.get(Department, faculty_id)
        if faculty is None:
            raise NotFoundError("Факультет не найден")
        if faculty.type not in {DepartmentType.FACULTY, DepartmentType.INSTITUTE}:
            raise ValidationError("Выберите факультет или институт")
        if actor.role not in MANAGERS and actor.department_id != faculty_id:
            raise ForbiddenError("График относится к другому факультету")

    async def current(self, faculty_id, period_id, actor, *, write=False, review=False):
        await self.authorize(faculty_id, actor, write=write, review=review)
        await PeriodService(self.session).get_by_id(period_id)
        query = select(FacultySchedule).where(
            FacultySchedule.faculty_id == faculty_id, FacultySchedule.period_id == period_id
        )
        if write or review:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def get(self, faculty_id, period_id, actor):
        schedule = await self.current(faculty_id, period_id, actor)
        if schedule is None:
            raise NotFoundError("График ещё не загружен")
        return schedule

    async def upload(self, faculty_id, period_id, filename, content, actor):
        await self.authorize(faculty_id, actor, write=True)
        # Serialize initial submissions too, before there is a schedule row to lock.
        await self.session.get(Department, faculty_id, with_for_update=True)
        schedule = await self.current(faculty_id, period_id, actor, write=True)
        await PeriodService(self.session).require_editable(period_id)
        if schedule and schedule.status != "REJECTED":
            raise ConflictError("Повторная загрузка доступна после отклонения деканом")
        if Path(filename).suffix.lower() != ".pdf":
            raise ValidationError("График необходимо загрузить в формате PDF")
        key = await run_in_threadpool(save_file, filename, content)
        if schedule is None:
            schedule = FacultySchedule(faculty_id=faculty_id, period_id=period_id)
            self.session.add(schedule)
        schedule.file_key = key
        schedule.status = "SUBMITTED"
        schedule.comment = None
        try:
            await self.session.flush()
            audit(self.session, actor, "schedule.upload", schedule.id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            storage_path(key).unlink(missing_ok=True)
            raise
        return schedule

    async def review(self, faculty_id, period_id, data, actor):
        schedule = await self.current(faculty_id, period_id, actor, review=True)
        await PeriodService(self.session).require_editable(period_id)
        if schedule is None:
            raise NotFoundError("График ещё не загружен")
        if schedule.status != "SUBMITTED":
            raise ConflictError("На рассмотрении нет новой версии графика")
        if not data.approved and not (data.comment or "").strip():
            raise ValidationError("Укажите замечание при отклонении графика")
        schedule.status = "APPROVED" if data.approved else "REJECTED"
        schedule.comment = None if data.approved else data.comment.strip()
        audit(self.session, actor, "schedule.review", schedule.id)
        await self.session.commit()
        return schedule
