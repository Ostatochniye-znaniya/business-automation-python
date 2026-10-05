from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.periods.models import TestingPeriod
from app.modules.periods.schemas import TestingPeriodCreate, TestingPeriodRead
from app.modules.periods.service import PeriodService

router = APIRouter(prefix="/periods", tags=["periods"])


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
) -> TestingPeriod:
    """Create a testing period and persist it."""
    return await service.create_period(data)
