from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.departments import management_service
from app.modules.departments.schemas import DepartmentCreate, DepartmentRead
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/department-management", tags=["departments"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("")
async def tree(session: Session, actor: Actor):
    return await management_service.tree(session, actor)


@router.post("", response_model=DepartmentRead, status_code=201)
async def create(data: DepartmentCreate, session: Session, actor: Actor):
    return await management_service.create(data, session, actor)


@router.put("/{department_id}", response_model=DepartmentRead)
async def update(department_id: int, data: DepartmentCreate, session: Session, actor: Actor):
    return await management_service.update(department_id, data, session, actor)


@router.delete("/{department_id}", status_code=204)
async def delete(department_id: int, session: Session, actor: Actor):
    return await management_service.delete(department_id, session, actor)
