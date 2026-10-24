from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.periods.models import TestingPeriod
from app.modules.periods.schemas import ReportPolicyUpdate, TestingPeriodCreate, TestingPeriodRead
from app.modules.periods.service import PeriodService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/periods", tags=["periods"])


@router.patch("/{period_id}/report-policy", response_model=TestingPeriodRead)
async def set_report_policy(
    period_id: int,
    data: ReportPolicyUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await PeriodService(session).set_report_policy(
        period_id, data.paper_reports_required, actor
    )


@router.put("/{period_id}", response_model=TestingPeriodRead)
async def update_period(
    period_id: int,
    data: TestingPeriodCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await PeriodService(session).update(period_id, data, actor)


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> PeriodService:
    return PeriodService(session)


@router.get("", response_model=list[TestingPeriodRead])
async def list_periods(
    service: Annotated[PeriodService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TestingPeriod]:
    """Return testing periods, newest start date first."""
    return await service.list_periods(offset=offset, limit=limit)


@router.get(
    "/{period_id}",
    response_model=TestingPeriodRead,
    responses={404: {"description": "TestingPeriod not found"}},
)
async def get_period(
    period_id: Annotated[int, Path(gt=0)],
    service: Annotated[PeriodService, Depends(get_service)],
) -> TestingPeriod:
    """Return one testing period or 404 when it does not exist."""
    return await service.get_by_id(period_id)


@router.post("", response_model=TestingPeriodRead, status_code=201)
async def create_period(
    data: TestingPeriodCreate,
    service: Annotated[PeriodService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
) -> TestingPeriod:
    """Create a testing period and persist it."""
    return await service.create_period(data, actor)
