from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.results.schemas import TestResultRead
from app.modules.results.service import ResultService

router = APIRouter(prefix="/results", tags=["results"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ResultService:
    return ResultService(session)


@router.get("", response_model=list[TestResultRead])
async def list_entities(
    service: Annotated[ResultService, Depends(get_service)],
    knowledge_test_id: Annotated[int, Query(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TestResultRead]:
    return await service.get_by_test(knowledge_test_id, offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=TestResultRead)
async def get_entity(
    entity_id: int, service: Annotated[ResultService, Depends(get_service)]
) -> TestResultRead:
    return await service.get_by_id(entity_id)
