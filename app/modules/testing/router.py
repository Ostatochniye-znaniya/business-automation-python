from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.testing.schemas import KnowledgeTestCreate, KnowledgeTestRead
from app.modules.testing.service import TestingService

router = APIRouter(prefix="/testing", tags=["testing"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> TestingService:
    return TestingService(session)


@router.get("", response_model=list[KnowledgeTestRead])
async def list_entities(
    service: Annotated[TestingService, Depends(get_service)],
    period_id: Annotated[int, Query(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[KnowledgeTestRead]:
    return await service.list_by_period(period_id, offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=KnowledgeTestRead)
async def get_entity(
    entity_id: int, service: Annotated[TestingService, Depends(get_service)]
) -> KnowledgeTestRead:
    return await service.get_by_id(entity_id)


@router.post("", response_model=KnowledgeTestRead, status_code=201)
async def create_entity(
    data: KnowledgeTestCreate, service: Annotated[TestingService, Depends(get_service)]
) -> KnowledgeTestRead:
    return await service.create(data)
