from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.departments.schemas import DepartmentRead
from app.modules.departments.service import DepartmentService

router = APIRouter(prefix="/departments", tags=["departments"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DepartmentService:
    return DepartmentService(session)


@router.get("", response_model=list[DepartmentRead])
async def list_entities(
    service: Annotated[DepartmentService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[DepartmentRead]:
    return await service.list_departments(offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=DepartmentRead)
async def get_entity(
    entity_id: int, service: Annotated[DepartmentService, Depends(get_service)]
) -> DepartmentRead:
    return await service.get_by_id(entity_id)
