from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.disciplines.schemas import DisciplineCreate, DisciplineRead
from app.modules.disciplines.service import DisciplineService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/disciplines", tags=["disciplines"])


@router.post("", response_model=DisciplineRead, status_code=201)
async def create(
    data: DisciplineCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await DisciplineService(session).save(data, actor)


@router.put("/{discipline_id}", response_model=DisciplineRead)
async def update(
    discipline_id: int,
    data: DisciplineCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await DisciplineService(session).save(data, actor, discipline_id)


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
