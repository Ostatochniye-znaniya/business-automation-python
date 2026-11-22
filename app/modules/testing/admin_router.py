from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import KnowledgeTestStatus
from app.db.dependencies import get_db_session
from app.modules.testing.admin_service import AdminCheckService
from app.modules.testing.schemas import AdminCheckRead, AdminChecksPage
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/administration/checks", tags=["administration"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("")
async def list_checks(
    session: Session,
    actor: Actor,
    search: Annotated[str | None, Query(max_length=255)] = None,
    period_id: Annotated[int | None, Query(gt=0)] = None,
    status: KnowledgeTestStatus | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminChecksPage:
    return await AdminCheckService(session).list_checks(
        actor, search=search, period_id=period_id, status=status, offset=offset, limit=limit
    )


@router.get("/{check_id}")
async def check_details(
    check_id: Annotated[int, Path(gt=0)], session: Session, actor: Actor
) -> AdminCheckRead:
    return await AdminCheckService(session).get_check(actor, check_id)
