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
from app.modules.testing.models import GroupParticipation, KnowledgeTest, TestAssignment
from app.modules.testing.schemas import (
    AgreementSave,
    AssignmentSave,
    AssignmentsSave,
    ParticipationSave,
)
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
            query = query.where(self.teacher_scope(actor.id))
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
        require_role(actor, PLANNERS | {UserRole.TEACHER, UserRole.DEPARTMENT_HEAD})
        test = await self.session.get(KnowledgeTest, test_id, with_for_update=write)
        if test is None:
            raise NotFoundError("Проверка не найдена")
        if actor.role == UserRole.TEACHER:
            if not any(a.teacher_id == actor.id for a in test.assignments) and (
                test.assignments or test.teacher_id != actor.id
            ):
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
        eligible = await self.eligible_teachers(test_id, actor)
        if data.teacher_id not in {teacher.id for teacher in eligible}:
            raise ValidationError("Преподаватель не может проводить эту дисциплину")
        teacher = await self.session.get(User, data.teacher_id)
        period = await PeriodService(self.session).get_by_id(test.period_id)
        scheduled = utc_naive(data.scheduled_at)
        if (
            not period.start_date
            <= scheduled.replace(tzinfo=UTC).astimezone(MOSCOW).date()
            <= period.end_date
        ):
            raise ValidationError("Дата проверки должна находиться внутри периода")
        await self.check_collision(test, teacher.id, scheduled)
        if len(test.assignments) > 1:
            raise ConflictError("Для нескольких преподавателей используйте список назначений")
        if test.assignments and test.assignments[0].teacher_id != teacher.id:
            test.assignments.clear()
            await self.session.flush()
        if not test.assignments:
            test.assignments.append(TestAssignment(teacher_id=teacher.id))
        assignment = test.assignments[0]
        assignment.start_date = assignment.end_date = (
            scheduled.replace(tzinfo=UTC).astimezone(MOSCOW).date()
        )
        assignment.scheduled_at = scheduled
        assignment.agreement_status = "PROPOSED"
        assignment.agreement_comment = None
        test.teacher_id = teacher.id
        test.scheduled_at = scheduled
        test.room = data.room
        test.agreement_status = "PROPOSED"
        test.agreement_comment = None
        audit(self.session, actor, "testing.assign", test.id)
        await self.session.commit()
        return test

    @staticmethod
    def teacher_scope(teacher_id):
        return KnowledgeTest.assignments.any(TestAssignment.teacher_id == teacher_id) | (
            ~KnowledgeTest.assignments.any() & (KnowledgeTest.teacher_id == teacher_id)
        )

    async def eligible_teachers(self, test_id, actor):
        test = await self.get_test(test_id, actor)
        discipline = await self.session.get(Discipline, test.discipline_id)
        query = select(User).where(User.is_active.is_(True), User.role == UserRole.TEACHER)
        if discipline.department_id is not None:
            query = query.where(User.department_id == discipline.department_id)
        return list((await self.session.scalars(query.order_by(User.full_name, User.id))).all())

    async def check_collision(self, test, teacher_id, scheduled):
        # Lock the teacher as well as the test to serialize competing reservations.
        await self.session.get(User, teacher_id, with_for_update=True)
        collision = await self.session.scalar(
            select(KnowledgeTest.id).where(
                KnowledgeTest.id != test.id,
                KnowledgeTest.status != KnowledgeTestStatus.CANCELLED,
                KnowledgeTest.assignments.any(
                    (TestAssignment.scheduled_at == scheduled)
                    & (
                        (TestAssignment.teacher_id == teacher_id)
                        | (KnowledgeTest.group_id == test.group_id)
                    )
                )
                | (
                    ~KnowledgeTest.assignments.any()
                    & (KnowledgeTest.scheduled_at == scheduled)
                    & (
                        (KnowledgeTest.teacher_id == teacher_id)
                        | (KnowledgeTest.group_id == test.group_id)
                    )
                ),
            )
        )
        if collision:
            raise ConflictError("У группы или преподавателя уже есть проверка в это время")

    async def save_assignments(self, test_id, data: AssignmentsSave, actor):
        require_role(actor, PLANNERS)
        test = await self.get_test(test_id, actor, write=True)
        if test.status != KnowledgeTestStatus.PLANNED:
            raise ConflictError("Назначения начавшейся или отменённой проверки изменять нельзя")
        discipline = await self.session.get(Discipline, test.discipline_id)
        await require_department(self.session, actor, discipline.department_id)
        eligible = {teacher.id for teacher in await self.eligible_teachers(test_id, actor)}
        if not set(data.teacher_ids) <= eligible:
            raise ValidationError("Преподаватель не может проводить эту дисциплину")
        period = await PeriodService(self.session).get_by_id(test.period_id)
        if not period.start_date <= data.start_date <= data.end_date <= period.end_date:
            raise ValidationError("Интервал проверки должен находиться внутри периода")
        existing = {a.teacher_id: a for a in test.assignments}
        assignments = []
        for teacher_id in data.teacher_ids:
            item = existing.get(teacher_id) or TestAssignment(teacher_id=teacher_id)
            if (item.start_date, item.end_date, test.room) != (
                data.start_date,
                data.end_date,
                data.room,
            ):
                item.scheduled_at = None
                item.agreement_status = "PROPOSED"
                item.agreement_comment = None
            item.start_date, item.end_date = data.start_date, data.end_date
            assignments.append(item)
        test.assignments = assignments
        test.room = data.room
        self.sync_assignment_summary(test)
        audit(self.session, actor, "testing.assign", test.id)
        await self.session.commit()
        return test

    @staticmethod
    def sync_assignment_summary(test):
        # Compatibility fields for existing clients and historical document templates.
        test.teacher_id = test.assignments[0].teacher_id if test.assignments else None
        dates = [a.scheduled_at for a in test.assignments if a.scheduled_at]
        test.scheduled_at = min(dates) if dates else None
        statuses = {a.agreement_status for a in test.assignments}
        test.agreement_status = (
            "AGREED"
            if statuses == {"AGREED"}
            else "REJECTED"
            if "REJECTED" in statuses
            else "PROPOSED"
        )
        test.agreement_comment = (
            test.assignments[0].agreement_comment if len(test.assignments) == 1 else None
        )

    async def agree(self, test_id: int, data: AgreementSave, actor: UserRead) -> KnowledgeTest:
        require_role(actor, {UserRole.TEACHER})
        test = await self.get_test(test_id, actor, write=True)
        if test.status != KnowledgeTestStatus.PLANNED:
            raise ConflictError("Согласование доступно только для запланированной проверки")
        if not data.approved and not (data.comment or "").strip():
            raise ValidationError("Укажите причину отклонения времени")
        if not test.assignments:
            test.assignments = [
                TestAssignment(
                    teacher_id=actor.id,
                    scheduled_at=test.scheduled_at,
                    agreement_status=test.agreement_status,
                )
            ]
        item = next(a for a in test.assignments if a.teacher_id == actor.id)
        if data.approved:
            scheduled = utc_naive(data.scheduled_at) if data.scheduled_at else item.scheduled_at
            if scheduled is None:
                raise ValidationError("Выберите дату проверки")
            day = scheduled.replace(tzinfo=UTC).astimezone(MOSCOW).date()
            if item.start_date and not item.start_date <= day <= item.end_date:
                raise ValidationError("Дата должна находиться внутри назначенного интервала")
            period = await PeriodService(self.session).get_by_id(test.period_id)
            if not period.start_date <= day <= period.end_date:
                raise ValidationError("Дата проверки должна находиться внутри периода")
            await self.check_collision(test, actor.id, scheduled)
            item.scheduled_at = scheduled
        else:
            item.scheduled_at = None
        item.agreement_status = "AGREED" if data.approved else "REJECTED"
        item.agreement_comment = data.comment
        self.sync_assignment_summary(test)
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
