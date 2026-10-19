from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.reports.schemas import ReportCreate, ReportRead, ReportUpdate
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


@router.get(
    "/{entity_id}",
    response_model=ReportRead,
    responses={404: {"description": "Report not found"}},
)
async def get_entity(
    entity_id: int, service: Annotated[ReportService, Depends(get_service)]
) -> ReportRead:
    return await service.get_by_id(entity_id)


@router.post(
    "",
    response_model=ReportRead,
    status_code=201,
    responses={
        404: {"description": "KnowledgeTest not found"},
        409: {"description": "Report for this knowledge test already exists"},
    },
)
async def create_entity(
    data: ReportCreate,
    service: Annotated[ReportService, Depends(get_service)],
) -> ReportRead:
    """Create one report per knowledge test."""
    return await service.create_report(data)


@router.put(
    "/{entity_id}",
    response_model=ReportRead,
    responses={404: {"description": "Report not found"}},
)
async def update_entity(
    entity_id: Annotated[int, Path(gt=0)],
    data: ReportUpdate,
    service: Annotated[ReportService, Depends(get_service)],
) -> ReportRead:
    """Update only the report fields sent in the request body."""
    return await service.update_report(entity_id, data)


@router.delete(
    "/{entity_id}",
    status_code=204,
    responses={404: {"description": "Report not found"}},
)
async def delete_entity(
    entity_id: Annotated[int, Path(gt=0)],
    service: Annotated[ReportService, Depends(get_service)],
) -> None:
    await service.delete_report(entity_id)
