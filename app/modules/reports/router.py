from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.reports.schemas import ReportRead
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReportService:
    return ReportService(session)


@router.get("", response_model=list[ReportRead])
async def list_entities(
    service: Annotated[ReportService, Depends(get_service)],
    knowledge_test_id: Annotated[int, Query(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ReportRead]:
    return await service.get_by_test(knowledge_test_id, offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=ReportRead)
async def get_entity(
    entity_id: int, service: Annotated[ReportService, Depends(get_service)]
) -> ReportRead:
    return await service.get_by_id(entity_id)
