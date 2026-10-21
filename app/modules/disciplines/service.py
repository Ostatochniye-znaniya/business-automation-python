from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.disciplines.models import Discipline
from app.modules.disciplines.schemas import DashboardStatistics, DisciplineCreate
from app.modules.users.schemas import UserRead


class DisciplineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self, data: DisciplineCreate, actor: UserRead, discipline_id: int | None = None
    ) -> Discipline:
        from app.core.permissions import MANAGERS, audit, require_role
        from app.modules.departments.service import DepartmentService

        require_role(actor, MANAGERS)
        if data.department_id:
            await DepartmentService(self.session).get_by_id(data.department_id)
        discipline = await self.get_by_id(discipline_id) if discipline_id else Discipline()
        for key, value in data.model_dump().items():
            setattr(discipline, key, value)
        self.session.add(discipline)
        await self.session.flush()
        audit(self.session, actor, "discipline.save", discipline.id)
        await self.session.commit()
        return discipline

    async def get_by_id(self, entity_id: int) -> Discipline:
        entity = await self.session.get(Discipline, entity_id)
        if entity is None:
            raise NotFoundError("Discipline not found")
        return entity

    async def list_disciplines(self, offset: int = 0, limit: int = 100) -> list[Discipline]:
        return list(
            (await self.session.scalars(select(Discipline).offset(offset).limit(limit))).all()
        )

    async def get_dashboard_statistics(
        self, period_id: int, department_id: int
    ) -> DashboardStatistics:
        from app.modules.departments.service import DepartmentService
        from app.modules.testing.service import TestingService

        ids = await DepartmentService(self.session).subtree_ids(department_id)
        testing = TestingService(self.session)
        return DashboardStatistics(
            required=2 * await testing.participation_count(period_id, ids),
            actual=await testing.scheduled_count(period_id, ids),
        )
