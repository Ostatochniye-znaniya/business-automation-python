from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.users import administration_service
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import AccessDecision, AccessRequestCreate, UserCreate, UserRead

router = APIRouter(prefix="/administration", tags=["administration"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("/me", response_model=UserRead)
async def current_user(actor: Actor):
    return await administration_service.current_user(actor)


@router.get("/users", response_model=list[UserRead])
async def users(
    session: Session,
    actor: Actor,
    offset: int = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await administration_service.users(session, actor, offset, limit)


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, session: Session, actor: Actor):
    return await administration_service.create_user(data, session, actor)


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserCreate, session: Session, actor: Actor):
    return await administration_service.update_user(user_id, data, session, actor)


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(user_id: int, session: Session, actor: Actor):
    return await administration_service.deactivate_user(user_id, session, actor)


@router.post("/access-requests", status_code=201)
async def request_access(data: AccessRequestCreate, session: Session, actor: Actor):
    return await administration_service.request_access(data, session, actor)


@router.get("/access-requests")
async def access_requests(
    session: Session,
    actor: Actor,
    offset: int = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await administration_service.access_requests(session, actor, offset, limit)


@router.put("/access-requests/{request_id}")
async def decide_access(request_id: int, data: AccessDecision, session: Session, actor: Actor):
    return await administration_service.decide_access(request_id, data, session, actor)


@router.get("/audit")
async def audit_events(
    session: Session,
    actor: Actor,
    offset: int = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await administration_service.audit_events(session, actor, offset, limit)


@router.get("/imports")
async def import_logs(session: Session, actor: Actor):
    return await administration_service.import_logs(session, actor)


@router.post("/imports/employees")
async def import_employees(
    file: UploadFile, session: Session, actor: Actor, deactivate_missing: bool = False
):
    from app.integrations.sync import ImportService

    return await ImportService(session).employees(
        file.filename or "", await file.read(5 * 1024 * 1024 + 1), actor, deactivate_missing
    )
