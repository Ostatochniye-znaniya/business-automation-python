from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.dashboard.schemas import DashboardRead
from app.modules.dashboard.service import DashboardService
from app.modules.departments.service import DepartmentService
from app.modules.disciplines.service import DisciplineService
from app.modules.groups.service import GroupService
from app.modules.periods.service import PeriodService
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DashboardService:
    return DashboardService(
        PeriodService(session),
        DepartmentService(session),
        GroupService(session),
        DisciplineService(session),
        ReportService(session),
    )


@router.get("", response_model=DashboardRead)
async def dashboard(
    period_id: Annotated[int, Query(gt=0)],
    service: Annotated[DashboardService, Depends(get_service)],
) -> DashboardRead:
    return await service.get_dashboard(period_id)
