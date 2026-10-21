from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.results.schemas import TestResultCreate, TestResultRead
from app.modules.results.service import ResultService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/results", tags=["results"])


@router.put("", response_model=TestResultRead)
async def save_result(
    data: TestResultCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await ResultService(session).save_result(data, actor)


@router.post("/complete/{test_id}")
async def complete(
    test_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    actor: Annotated[UserRead, Depends(get_current_user)],
):
    return await ResultService(session).complete(test_id, actor)


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ResultService:
    return ResultService(session)


@router.get("", response_model=list[TestResultRead])
async def list_entities(
    service: Annotated[ResultService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    knowledge_test_id: Annotated[int, Query(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TestResultRead]:
    from app.modules.testing.workflow import TestingWorkflow

    await TestingWorkflow(service.session).get_test(knowledge_test_id, actor)
    return await service.get_by_test(knowledge_test_id, offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=TestResultRead)
async def get_entity(
    entity_id: int,
    service: Annotated[ResultService, Depends(get_service)],
    actor: Annotated[UserRead, Depends(get_current_user)],
) -> TestResultRead:
    entity = await service.get_by_id(entity_id)
    from app.modules.testing.workflow import TestingWorkflow

    await TestingWorkflow(service.session).get_test(entity.knowledge_test_id, actor)
    return entity
