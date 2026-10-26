from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.groups.schemas import (
    GroupSave,
    StudyGroupRead,
    StudyProgramCreate,
    StudyProgramRead,
)
from app.modules.groups.service import GroupService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/catalog", tags=["catalogs"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.post("/groups", response_model=StudyGroupRead, status_code=201)
async def create_group(data: GroupSave, session: Session, actor: Actor):
    return await GroupService(session).save_group(data, actor)


@router.put("/groups/{group_id}", response_model=StudyGroupRead)
async def update_group(group_id: int, data: GroupSave, session: Session, actor: Actor):
    return await GroupService(session).save_group(data, actor, group_id)


@router.post("/programs", response_model=StudyProgramRead, status_code=201)
async def create_program(data: StudyProgramCreate, session: Session, actor: Actor):
    return await GroupService(session).save_program(data, actor)


@router.put("/programs/{program_id}", response_model=StudyProgramRead)
async def update_program(program_id: int, data: StudyProgramCreate, session: Session, actor: Actor):
    return await GroupService(session).save_program(data, actor, program_id)
