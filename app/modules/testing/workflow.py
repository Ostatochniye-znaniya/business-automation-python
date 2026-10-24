from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import KnowledgeTestStatus, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, PLANNERS, audit, require_department, require_role
from app.core.time import MOSCOW, utc_naive
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup, StudyProgram
from app.modules.groups.recommendation_models import GroupRecommendation
from app.modules.periods.service import PeriodService
from app.modules.students.models import Student
from app.modules.testing.models import GroupParticipation, KnowledgeTest
from app.modules.testing.schemas import AgreementSave, AssignmentSave, ParticipationSave
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


class TestingWorkflow:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tests(
        self, period_id: int, actor: UserRead, offset: int = 0, limit: int = 100
    ) -> list[KnowledgeTest]:
        from app.modules.departments.service import DepartmentService

        require_role(actor, PLANNERS | {UserRole.TEACHER, UserRole.DEPARTMENT_HEAD})
        query = select(KnowledgeTest).where(KnowledgeTest.period_id == period_id)
        if actor.role == UserRole.TEACHER:
            query = query.where(KnowledgeTest.teacher_id == actor.id)
        elif actor.role not in MANAGERS:
            ids = await DepartmentService(self.session).subtree_ids(actor.department_id)
            group_scope = StudyGroup.department_id.in_(ids) | (
                StudyGroup.department_id.is_(None) & StudyProgram.faculty_id.in_(ids)
            )
            query = (
                query.join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id)
                .join(Discipline, Discipline.id == KnowledgeTest.discipline_id)
                .outerjoin(StudyProgram, StudyProgram.id == StudyGroup.study_program_id)
                .where(
                    group_scope
                    if actor.role == UserRole.DEPARTMENT_HEAD
                    else group_scope | Discipline.department_id.in_(ids)
                )
            )
        return list(
            (
                await self.session.scalars(
                    query.order_by(KnowledgeTest.id).offset(offset).limit(limit)
                )
            ).all()
        )

    async def get_test(
        self, test_id: int, actor: UserRead, *, write: bool = False
    ) -> KnowledgeTest:
        test = await self.session.get(KnowledgeTest, test_id, with_for_update=write)
        if test is None:
            raise NotFoundError("Проверка не найдена")
        if actor.role == UserRole.TEACHER:
            if test.teacher_id != actor.id:
                raise ForbiddenError("Проверка закреплена за другим преподавателем")
        else:
            require_role(actor, PLANNERS | {UserRole.DEPARTMENT_HEAD})
            group = await self.session.get(StudyGroup, test.group_id)
            discipline = await self.session.get(Discipline, test.discipline_id)
            if actor.role not in MANAGERS:
                if actor.role == UserRole.DEPARTMENT_HEAD:
                    from app.modules.departments.service import DepartmentService
                    from app.modules.groups.service import GroupService

                    ids = await DepartmentService(self.session).subtree_ids(actor.department_id)
                    if not await GroupService(self.session).belongs_to_departments(group.id, ids):
                        raise ForbiddenError("Данные относятся к другому факультету")
                else:
                    try:
                        await require_department(self.session, actor, group.department_id)
                    except ForbiddenError:
                        await require_department(self.session, actor, discipline.department_id)
        if write:
            await PeriodService(self.session).require_editable(test.period_id)
        return test

    async def select_group(self, data: ParticipationSave, actor: UserRead) -> GroupParticipation:
        require_role(actor, PLANNERS)
        await PeriodService(self.session).require_editable(data.period_id)
        group = await self.session.get(StudyGroup, data.group_id, with_for_update=True)
        if group is None:
            raise NotFoundError("Группа не найдена")
        await require_department(self.session, actor, group.department_id)
        recommendation = await self.session.scalar(
            select(GroupRecommendation).where(
                GroupRecommendation.group_id == data.group_id,
                GroupRecommendation.period_id == data.period_id,
                GroupRecommendation.recommended.is_(True),
            )
        )
        if recommendation is None:
            raise ValidationError("Группа отсутствует в рекомендованном списке периода")
        disciplines = list(
            (
                await self.session.scalars(
                    select(Discipline).where(Discipline.id.in_(data.discipline_ids))
                )
            ).all()
        )
        if len(disciplines) != len(data.discipline_ids):
            raise NotFoundError("Дисциплина не найдена")
        existing = list(
            (
                await self.session.scalars(
                    select(KnowledgeTest)
                    .where(
                        KnowledgeTest.group_id == data.group_id,
                        KnowledgeTest.period_id == data.period_id,
                        KnowledgeTest.status != KnowledgeTestStatus.CANCELLED,
                    )
                    .with_for_update()
                )
            ).all()
        )
        wanted = set(data.discipline_ids)
        for test in existing:
            if test.discipline_id not in wanted:
                if test.status != KnowledgeTestStatus.PLANNED:
                    raise ConflictError("Начавшуюся проверку нельзя исключить из плана")
                test.status = KnowledgeTestStatus.CANCELLED
        current = {test.discipline_id for test in existing}
        for discipline_id in wanted - current:
            self.session.add(
                KnowledgeTest(
                    group_id=data.group_id, period_id=data.period_id, discipline_id=discipline_id
                )
            )
        membership = await self.session.scalar(
            select(GroupParticipation).where(
                GroupParticipation.group_id == data.group_id,
                GroupParticipation.period_id == data.period_id,
            )
        )
        if membership is None:
            membership = GroupParticipation(group_id=data.group_id, period_id=data.period_id)
            self.session.add(membership)
        membership.participates = data.participates
        membership.reason = data.reason
        audit(self.session, actor, "testing.select_group", group.id)
        await self.session.commit()
        return membership

    async def assign(self, test_id: int, data: AssignmentSave, actor: UserRead) -> KnowledgeTest:
        require_role(actor, PLANNERS)
        test = await self.get_test(test_id, actor, write=True)
        if test.status != KnowledgeTestStatus.PLANNED:
            raise ConflictError("Расписание начавшейся или отменённой проверки изменять нельзя")
        discipline = await self.session.get(Discipline, test.discipline_id)
        await require_department(self.session, actor, discipline.department_id)
        teacher = await self.session.get(User, data.teacher_id)
        if teacher is None or not teacher.is_active or teacher.role != UserRole.TEACHER:
            raise ValidationError("Выберите действующего преподавателя")
        if discipline.department_id and teacher.department_id != discipline.department_id:
            raise ValidationError("Преподаватель должен относиться к кафедре дисциплины")
        period = await PeriodService(self.session).get_by_id(test.period_id)
        scheduled = utc_naive(data.scheduled_at)
        if (
            not period.start_date
            <= scheduled.replace(tzinfo=UTC).astimezone(MOSCOW).date()
            <= period.end_date
        ):
            raise ValidationError("Дата проверки должна находиться внутри периода")
        collision = await self.session.scalar(
            select(KnowledgeTest.id).where(
                KnowledgeTest.id != test.id,
                KnowledgeTest.scheduled_at == scheduled,
                KnowledgeTest.status != KnowledgeTestStatus.CANCELLED,
                (
                    (KnowledgeTest.teacher_id == teacher.id)
                    | (KnowledgeTest.group_id == test.group_id)
                ),
            )
        )
        if collision:
            raise ConflictError("У группы или преподавателя уже есть проверка в это время")
        test.teacher_id = teacher.id
        test.scheduled_at = scheduled
        test.room = data.room
        test.agreement_status = "PROPOSED"
        test.agreement_comment = None
        audit(self.session, actor, "testing.assign", test.id)
        await self.session.commit()
        return test

    async def agree(self, test_id: int, data: AgreementSave, actor: UserRead) -> KnowledgeTest:
        require_role(actor, {UserRole.TEACHER})
        test = await self.get_test(test_id, actor, write=True)
        if test.status != KnowledgeTestStatus.PLANNED or not test.scheduled_at:
            raise ConflictError("Сначала необходимо назначить дату проверки")
        if not data.approved and not (data.comment or "").strip():
            raise ValidationError("Укажите причину отклонения времени")
        test.agreement_status = "AGREED" if data.approved else "REJECTED"
        test.agreement_comment = data.comment
        audit(self.session, actor, "testing.agree", test.id)
        await self.session.commit()
        return test

    async def roster(self, test_id: int, actor: UserRead) -> list[Student]:
        test = await self.get_test(test_id, actor)
        return list(
            (
                await self.session.scalars(
                    select(Student)
                    .where(Student.group_id == test.group_id)
                    .order_by(Student.full_name)
                )
            ).all()
        )
