from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.users.dependencies import get_current_user, require_staff
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> UserService:
    return UserService(session)


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_staff)])
async def list_entities(
    service: Annotated[UserService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[UserRead]:
    return await service.list_users(offset=offset, limit=limit)


@router.get("/me", response_model=UserRead)
async def current_user(actor: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
    return actor


@router.get("/{entity_id}", response_model=UserRead, dependencies=[Depends(require_staff)])
async def get_entity(
    entity_id: int, service: Annotated[UserService, Depends(get_service)]
) -> UserRead:
    return await service.get_by_id(entity_id)
