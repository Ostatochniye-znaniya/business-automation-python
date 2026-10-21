from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.groups.schemas import GroupTestingOverview, StudyGroupRead, StudyProgramRead
from app.modules.groups.service import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])
programs_router = APIRouter(prefix="/programs", tags=["groups"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> GroupService:
    return GroupService(session)


@router.get("", response_model=list[StudyGroupRead])
async def list_entities(
    service: Annotated[GroupService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    faculty_id: Annotated[int | None, Query(gt=0)] = None,
    study_program_id: Annotated[int | None, Query(gt=0)] = None,
    academic_year: Annotated[str | None, Query(pattern=r"^\d{4}/\d{4}$")] = None,
    semester: Annotated[int | None, Query(ge=1, le=2)] = None,
) -> list[StudyGroupRead]:
    return await service.list_groups(
        offset=offset,
        limit=limit,
        faculty_id=faculty_id,
        study_program_id=study_program_id,
        academic_year=academic_year,
        semester=semester,
    )


@router.get("/testing-overview", response_model=list[GroupTestingOverview])
async def testing_overview(
    service: Annotated[GroupService, Depends(get_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    faculty_id: Annotated[int | None, Query(gt=0)] = None,
    study_program_id: Annotated[int | None, Query(gt=0)] = None,
    academic_year: Annotated[str | None, Query(pattern=r"^\d{4}/\d{4}$")] = None,
    semester: Annotated[int | None, Query(ge=1, le=2)] = None,
) -> list[GroupTestingOverview]:
    return await service.testing_overview(
        offset=offset,
        limit=limit,
        faculty_id=faculty_id,
        study_program_id=study_program_id,
        academic_year=academic_year,
        semester=semester,
    )


@router.get("/{entity_id}", response_model=StudyGroupRead)
async def get_entity(
    entity_id: int, service: Annotated[GroupService, Depends(get_service)]
) -> StudyGroupRead:
    return await service.get_by_id(entity_id)


@programs_router.get("", response_model=list[StudyProgramRead])
async def list_programs(
    service: Annotated[GroupService, Depends(get_service)],
    faculty_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[StudyProgramRead]:
    return await service.list_programs(faculty_id=faculty_id, offset=offset, limit=limit)
