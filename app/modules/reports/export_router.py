from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.reports.exports import ExportService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/exports", tags=["exports"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("/report/{test_id}.docx")
async def report(test_id: int, session: Session, actor: Actor):
    content = await ExportService(session).report(test_id, actor)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="report-{test_id}.docx"'},
    )


@router.get("/summary/{period_id}.csv")
async def summary(period_id: int, session: Session, actor: Actor):
    content = await ExportService(session).summary(period_id, actor)
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="summary-{period_id}.csv"'},
    )


@router.get("/schedule/{period_id}.pdf")
async def schedule(
    period_id: int,
    session: Session,
    actor: Actor,
    department_id: int | None = None,
    signatory: Annotated[str, Query(max_length=255)] = "",
):
    content = await ExportService(session).schedule(period_id, actor, department_id, signatory)
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="schedule-{period_id}.pdf"'},
    )
