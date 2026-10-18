from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.groups.schemas import DashboardStatistics
from app.modules.periods.models import TestingPeriod


class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> StudyGroup:
        entity = await self.session.get(StudyGroup, entity_id)
        if entity is None:
            raise NotFoundError("StudyGroup not found")
        return entity

    async def list_programs(
        self, faculty_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[StudyProgram]:
        statement = select(StudyProgram)
        if faculty_id is not None:
            statement = statement.where(StudyProgram.faculty_id == faculty_id)
        statement = (
            statement.order_by(StudyProgram.name, StudyProgram.id).offset(offset).limit(limit)
        )
        return list((await self.session.scalars(statement)).all())

    async def list_groups(
        self,
        offset: int = 0,
        limit: int = 100,
        *,
        faculty_id: int | None = None,
        study_program_id: int | None = None,
        academic_year: str | None = None,
        semester: int | None = None,
    ) -> list[StudyGroup]:
        statement = select(StudyGroup)
        if faculty_id is not None:
            statement = statement.join(StudyProgram).where(StudyProgram.faculty_id == faculty_id)
        if study_program_id is not None:
            statement = statement.where(StudyGroup.study_program_id == study_program_id)
        if academic_year is not None or semester is not None:
            membership = (
                select(GroupPeriod.group_id)
                .join(TestingPeriod)
                .where(GroupPeriod.group_id == StudyGroup.id)
            )
            if academic_year is not None:
                membership = membership.where(TestingPeriod.academic_year == academic_year)
            if semester is not None:
                membership = membership.where(TestingPeriod.semester == semester)
            statement = statement.where(membership.exists())
        statement = statement.order_by(StudyGroup.name, StudyGroup.id).offset(offset).limit(limit)
        return list((await self.session.scalars(statement)).all())

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> DashboardStatistics:
        """Unknown indicators are represented by null, never fabricated counts."""
        # TODO: agree period scope, required counts and report status rules with customer.
        return DashboardStatistics()
