from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.groups.recommendation_schemas import (
    RecommendationHistoryRead,
    RecommendationRead,
    RecommendationSave,
)
from app.modules.groups.recommendations import RecommendationService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> RecommendationService:
    return RecommendationService(session)


@router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    service: Annotated[RecommendationService, Depends(get_service)],
    period_id: Annotated[int | None, Query(gt=0)] = None,
    group_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await service.list_recommendations(
        period_id=period_id, group_id=group_id, offset=offset, limit=limit
    )


@router.put("", response_model=list[RecommendationRead])
async def save_recommendations(
    data: RecommendationSave,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RecommendationService, Depends(get_service)],
):
    return await service.save(data, actor)


@router.get("/history", response_model=list[RecommendationHistoryRead])
async def history(
    group_id: Annotated[int, Query(gt=0)],
    service: Annotated[RecommendationService, Depends(get_service)],
    period_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await service.history(group_id, period_id=period_id, offset=offset, limit=limit)


@router.get("/export")
async def export(
    period_id: Annotated[int, Query(gt=0)],
    service: Annotated[RecommendationService, Depends(get_service)],
    faculty_id: Annotated[int | None, Query(gt=0)] = None,
    study_program_id: Annotated[int | None, Query(gt=0)] = None,
):
    content = await service.export(
        period_id, faculty_id=faculty_id, study_program_id=study_program_id
    )
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="recommended-groups-{period_id}.csv"',
            "Cache-Control": "no-store",
        },
    )
