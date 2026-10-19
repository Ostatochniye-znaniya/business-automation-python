from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.testing.schemas import KnowledgeTestCreate, KnowledgeTestRead
from app.modules.testing.service import TestingService
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/testing", tags=["testing"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> TestingService:
    return TestingService(session)


@router.get("", response_model=list[KnowledgeTestRead])
async def list_entities(
    service: Annotated[TestingService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    period_id: Annotated[int, Query(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[KnowledgeTestRead]:
    return await TestingWorkflow(service.session).list_tests(period_id, actor, offset, limit)


@router.get("/{entity_id}", response_model=KnowledgeTestRead)
async def get_entity(
    entity_id: int,
    service: Annotated[TestingService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
) -> KnowledgeTestRead:
    return await TestingWorkflow(service.session).get_test(entity_id, actor)


@router.post("", response_model=KnowledgeTestRead, status_code=201)
async def create_entity(
    data: KnowledgeTestCreate,
    service: Annotated[TestingService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
) -> KnowledgeTestRead:
    return await service.create(data, actor)
