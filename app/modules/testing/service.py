from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import GroupPeriod, StudyGroup
from app.modules.periods.models import TestingPeriod
from app.modules.testing.models import KnowledgeTest
from app.modules.testing.schemas import KnowledgeTestCreate
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


class TestingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def participation_count(self, period_id: int, department_ids: set[int]) -> int:
        from sqlalchemy import func

        from app.modules.testing.models import GroupParticipation

        return (
            await self.session.scalar(
                select(func.count(GroupParticipation.id))
                .join(StudyGroup, StudyGroup.id == GroupParticipation.group_id)
                .where(
                    GroupParticipation.period_id == period_id,
                    GroupParticipation.participates.is_(True),
                    StudyGroup.department_id.in_(department_ids),
                )
            )
        ) or 0

    async def scheduled_count(self, period_id: int, department_ids: set[int]) -> int:
        from sqlalchemy import func

        from app.core.enums import KnowledgeTestStatus

        return (
            await self.session.scalar(
                select(func.count(KnowledgeTest.id))
                .join(StudyGroup, StudyGroup.id == KnowledgeTest.group_id)
                .where(
                    KnowledgeTest.period_id == period_id,
                    KnowledgeTest.status != KnowledgeTestStatus.CANCELLED,
                    StudyGroup.department_id.in_(department_ids),
                )
            )
        ) or 0

    async def get_by_id(self, entity_id: int) -> KnowledgeTest:
        entity = await self.session.get(KnowledgeTest, entity_id)
        if entity is None:
            raise NotFoundError("KnowledgeTest not found")
        return entity

    async def list_by_period(
        self, period_id: int, offset: int = 0, limit: int = 100
    ) -> list[KnowledgeTest]:
        return list(
            (
                await self.session.scalars(
                    select(KnowledgeTest)
                    .where(KnowledgeTest.period_id == period_id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def create(self, data: KnowledgeTestCreate, actor: UserRead) -> KnowledgeTest:
        from app.core.enums import KnowledgeTestStatus
        from app.core.exceptions import ConflictError, ValidationError
        from app.core.permissions import MANAGERS, audit, require_role
        from app.modules.periods.service import PeriodService

        require_role(actor, MANAGERS)
        await PeriodService(self.session).require_editable(data.period_id)
        if data.status != KnowledgeTestStatus.PLANNED:
            raise ValidationError("Новая проверка создаётся только в статусе PLANNED")
        for model, entity_id in (
            (StudyGroup, data.group_id),
            (TestingPeriod, data.period_id),
            (Discipline, data.discipline_id),
            (User, data.teacher_id),
        ):
            if entity_id is not None and await self.session.get(model, entity_id) is None:
                raise NotFoundError(f"{model.__name__} not found")
        if await self.session.get(GroupPeriod, (data.group_id, data.period_id)) is None:
            self.session.add(GroupPeriod(group_id=data.group_id, period_id=data.period_id))
        if await self.session.scalar(
            select(KnowledgeTest.id).where(
                KnowledgeTest.group_id == data.group_id,
                KnowledgeTest.period_id == data.period_id,
                KnowledgeTest.discipline_id == data.discipline_id,
                KnowledgeTest.status != KnowledgeTestStatus.CANCELLED,
            )
        ):
            raise ConflictError("Проверка группы по этой дисциплине уже существует")
        entity = KnowledgeTest(**data.model_dump())
        self.session.add(entity)
        audit(self.session, actor, "testing.create")
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update_schedule(
        self, test_id: int, scheduled_at: datetime, actor: UserRead
    ) -> KnowledgeTest:
        """Propose a new time using the same scope and agreement rules as assignment."""
        from app.core.exceptions import ValidationError
        from app.modules.testing.schemas import AssignmentSave
        from app.modules.testing.workflow import TestingWorkflow

        entity = await self.get_by_id(test_id)
        if entity.teacher_id is None or not entity.room:
            raise ValidationError("Сначала назначьте преподавателя и аудиторию")
        return await TestingWorkflow(self.session).assign(
            test_id,
            AssignmentSave(
                teacher_id=entity.teacher_id, scheduled_at=scheduled_at, room=entity.room
            ),
            actor,
        )
