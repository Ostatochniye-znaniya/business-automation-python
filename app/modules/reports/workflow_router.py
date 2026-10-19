from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.dependencies import get_db_session
from app.modules.reports.files import existing_file
from app.modules.reports.schemas import ReportMetadata, ReportRead, ReviewSave
from app.modules.reports.service import ReportService
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/report-workflow", tags=["report workflow"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.put("/{report_id}/metadata", response_model=ReportRead)
async def save_metadata(report_id: int, data: ReportMetadata, session: Session, actor: Actor):
    return await ReportService(session).metadata(report_id, data, actor)


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: int, session: Session, actor: Actor):
    await ReportService(session).delete(report_id, actor)


@router.get("", response_model=list[ReportRead])
async def review_queue(
    session: Session,
    actor: Actor,
    period_id: int | None = None,
    faculty_id: int | None = None,
    group_id: int | None = None,
    discipline_id: int | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await ReportService(session).list_for_review(
        actor, period_id, faculty_id, group_id, discipline_id, max(0, offset), limit
    )


@router.post("/testing/{test_id}", response_model=ReportRead, status_code=201)
async def create_report(test_id: int, session: Session, actor: Actor):
    return await ReportService(session).create(test_id, actor)


@router.post("/{report_id}/file", response_model=ReportRead)
async def upload(report_id: int, file: UploadFile, session: Session, actor: Actor):
    content = await file.read(get_settings().MAX_REPORT_BYTES + 1)
    return await ReportService(session).upload_electronic(
        report_id, file.filename or "", content, actor
    )


@router.get("/{report_id}/file")
async def download(report_id: int, session: Session, actor: Actor):
    report = await ReportService(session).get_by_id(report_id)
    await TestingWorkflow(session).get_test(report.knowledge_test_id, actor)
    path = existing_file(report.electronic_file_key)
    return FileResponse(
        path,
        filename=f"report-{report_id}{path.suffix}",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/{report_id}/withdraw", response_model=ReportRead)
async def withdraw(report_id: int, session: Session, actor: Actor):
    return await ReportService(session).withdraw(report_id, actor)


@router.put("/{report_id}/review/{version}", response_model=ReportRead)
async def review(
    report_id: int,
    version: Literal["electronic", "paper"],
    data: ReviewSave,
    session: Session,
    actor: Actor,
):
    return await ReportService(session).review(
        report_id, version, data.approved, data.comment, actor
    )
