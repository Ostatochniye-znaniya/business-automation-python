from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.groups.schemas import StudyGroupRead
from app.modules.groups.service import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> GroupService:
    return GroupService(session)


@router.get("", response_model=list[StudyGroupRead])
async def list_entities(
    service: Annotated[GroupService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[StudyGroupRead]:
    return await service.list_groups(offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=StudyGroupRead)
async def get_entity(
    entity_id: int, service: Annotated[GroupService, Depends(get_service)]
) -> StudyGroupRead:
    return await service.get_by_id(entity_id)
