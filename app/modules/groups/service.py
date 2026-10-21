from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.groups.recommendation_models import GroupRecommendation
from app.modules.groups.recommendations import RecommendationService
from app.modules.groups.schemas import (
    DashboardStatistics,
    GroupSave,
    GroupTestingOverview,
    GroupTestingSummary,
    StudyGroupRead,
    StudyProgramCreate,
)
from app.modules.periods.models import TestingPeriod
from app.modules.testing.models import KnowledgeTest
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def eligible_groups(self, period_id: int, actor: UserRead) -> list[StudyGroup]:
        from app.core.permissions import MANAGERS, PLANNERS, require_role
        from app.modules.departments.service import DepartmentService

        require_role(actor, PLANNERS)
        query = (
            select(StudyGroup)
            .join(GroupRecommendation, GroupRecommendation.group_id == StudyGroup.id)
            .where(
                GroupRecommendation.period_id == period_id,
                GroupRecommendation.recommended.is_(True),
            )
        )
        if actor.role not in MANAGERS:
            ids = await DepartmentService(self.session).subtree_ids(actor.department_id)
            query = query.where(StudyGroup.department_id.in_(ids))
        return list((await self.session.scalars(query.order_by(StudyGroup.name))).all())

    async def get_program(self, program_id: int) -> StudyProgram:
        program = await self.session.get(StudyProgram, program_id)
        if program is None:
            raise NotFoundError("Направление подготовки не найдено")
        return program

    async def save_program(
        self, data: StudyProgramCreate, actor: UserRead, program_id: int | None = None
    ) -> StudyProgram:
        from app.core.permissions import MANAGERS, audit, require_role
        from app.modules.departments.service import DepartmentService

        require_role(actor, MANAGERS)
        await DepartmentService(self.session).get_by_id(data.faculty_id)
        program = await self.get_program(program_id) if program_id else StudyProgram()
        for key, value in data.model_dump().items():
            setattr(program, key, value)
        self.session.add(program)
        await self.session.flush()
        audit(self.session, actor, "program.save", program.id)
        await self.session.commit()
        return program

    async def save_group(
        self, data: GroupSave, actor: UserRead, group_id: int | None = None
    ) -> StudyGroup:
        from app.core.permissions import MANAGERS, audit, require_role
        from app.modules.departments.service import DepartmentService
        from app.modules.periods.service import PeriodService

        require_role(actor, MANAGERS)
        if data.department_id:
            await DepartmentService(self.session).get_by_id(data.department_id)
        if data.study_program_id:
            await self.get_program(data.study_program_id)
        for period_id in data.period_ids:
            await PeriodService(self.session).get_by_id(period_id)
        group = await self.get_by_id(group_id) if group_id else StudyGroup()
        for key, value in data.model_dump(exclude={"period_ids"}).items():
            setattr(group, key, value)
        self.session.add(group)
        await self.session.flush()
        for period_id in set(data.period_ids):
            if await self.session.get(GroupPeriod, (group.id, period_id)) is None:
                self.session.add(GroupPeriod(group_id=group.id, period_id=period_id))
        audit(self.session, actor, "group.save", group.id)
        await self.session.commit()
        return group

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

    async def testing_overview(
        self,
        offset: int = 0,
        limit: int = 100,
        *,
        faculty_id: int | None = None,
        study_program_id: int | None = None,
        academic_year: str | None = None,
        semester: int | None = None,
    ) -> list[GroupTestingOverview]:
        groups = await self.list_groups(
            offset=offset,
            limit=limit,
            faculty_id=faculty_id,
            study_program_id=study_program_id,
            academic_year=academic_year,
            semester=semester,
        )
        if not groups:
            return []
        tests = (
            await self.session.execute(
                select(KnowledgeTest, Discipline.name)
                .join(Discipline)
                .where(KnowledgeTest.group_id.in_([group.id for group in groups]))
                .order_by(KnowledgeTest.period_id, KnowledgeTest.id)
            )
        ).all()
        by_group: dict[int, list[GroupTestingSummary]] = {group.id: [] for group in groups}
        for test, discipline_name in tests:
            by_group[test.group_id].append(
                GroupTestingSummary(
                    id=test.id,
                    period_id=test.period_id,
                    discipline_name=discipline_name,
                    scheduled_at=test.scheduled_at,
                    status=test.status,
                )
            )
        recommendations = (
            await self.session.execute(
                select(GroupRecommendation, User.full_name)
                .join(User, User.id == GroupRecommendation.changed_by_id)
                .where(GroupRecommendation.group_id.in_([group.id for group in groups]))
                .order_by(GroupRecommendation.period_id)
            )
        ).all()
        by_recommendation = {group.id: [] for group in groups}
        for record, name in recommendations:
            by_recommendation[record.group_id].append(RecommendationService.read(record, name))
        membership_rows = (
            await self.session.execute(
                select(GroupPeriod.group_id, GroupPeriod.period_id).where(
                    GroupPeriod.group_id.in_(by_group)
                )
            )
        ).all()
        memberships = {group.id: [] for group in groups}
        for group_id, period_id in membership_rows:
            memberships[group_id].append(period_id)
        return [
            GroupTestingOverview(
                **StudyGroupRead.model_validate(group).model_dump(),
                testings=by_group[group.id],
                recommendations=by_recommendation[group.id],
                enrolled_period_ids=memberships[group.id],
            )
            for group in groups
        ]

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> DashboardStatistics:
        from sqlalchemy import func

        from app.modules.departments.service import DepartmentService
        from app.modules.testing.service import TestingService

        ids = await DepartmentService(self.session).subtree_ids(department_id)
        required = await self.session.scalar(
            select(func.count(GroupRecommendation.id))
            .join(StudyGroup, StudyGroup.id == GroupRecommendation.group_id)
            .where(
                GroupRecommendation.period_id == period_id,
                GroupRecommendation.recommended.is_(True),
                StudyGroup.department_id.in_(ids),
            )
        )
        actual = await TestingService(self.session).participation_count(period_id, ids)
        return DashboardStatistics(required=required or 0, actual=actual)
