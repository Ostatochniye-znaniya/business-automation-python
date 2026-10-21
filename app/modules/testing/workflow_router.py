from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.testing.schemas import (
    AgreementSave,
    AssignmentSave,
    KnowledgeTestRead,
    ParticipationSave,
)
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/workflow", tags=["testing workflow"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("/testing", response_model=list[KnowledgeTestRead])
async def visible_tests(
    period_id: int,
    session: Session,
    actor: Actor,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await TestingWorkflow(session).list_tests(period_id, actor, offset, limit)


@router.get("/eligible-groups")
async def eligible_groups(period_id: int, session: Session, actor: Actor):
    from app.modules.groups.schemas import StudyGroupRead
    from app.modules.groups.service import GroupService

    return [
        StudyGroupRead.model_validate(group)
        for group in await GroupService(session).eligible_groups(period_id, actor)
    ]


@router.put("/participation")
async def select_group(data: ParticipationSave, session: Session, actor: Actor):
    return await TestingWorkflow(session).select_group(data, actor)


@router.put("/testing/{test_id}/assignment")
async def assignment(test_id: int, data: AssignmentSave, session: Session, actor: Actor):
    return await TestingWorkflow(session).assign(test_id, data, actor)


@router.put("/testing/{test_id}/agreement")
async def agreement(test_id: int, data: AgreementSave, session: Session, actor: Actor):
    return await TestingWorkflow(session).agree(test_id, data, actor)


@router.get("/testing/{test_id}/roster")
async def roster(test_id: int, session: Session, actor: Actor):
    return await TestingWorkflow(session).roster(test_id, actor)
