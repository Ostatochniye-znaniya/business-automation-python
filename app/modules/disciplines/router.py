from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.disciplines.schemas import DisciplineRead
from app.modules.disciplines.service import DisciplineService

router = APIRouter(prefix="/disciplines", tags=["disciplines"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DisciplineService:
    return DisciplineService(session)


@router.get("", response_model=list[DisciplineRead])
async def list_entities(
    service: Annotated[DisciplineService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[DisciplineRead]:
    return await service.list_disciplines(offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=DisciplineRead)
async def get_entity(
    entity_id: int, service: Annotated[DisciplineService, Depends(get_service)]
) -> DisciplineRead:
    return await service.get_by_id(entity_id)
