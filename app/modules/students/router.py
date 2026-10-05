from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.students.models import Student
from app.modules.students.schemas import StudentRead
from app.modules.students.service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


def get_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> StudentService:
    return StudentService(session)


@router.get("", response_model=list[StudentRead])
async def list_students(
    service: Annotated[StudentService, Depends(get_service)],
    group_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Student]:
    """Return students, optionally filtered by study group."""
    return await service.list_students(group_id=group_id, offset=offset, limit=limit)


@router.get(
    "/{student_id}",
    response_model=StudentRead,
    responses={404: {"description": "Student not found"}},
)
async def get_student(
    student_id: Annotated[int, Path(gt=0)],
    service: Annotated[StudentService, Depends(get_service)],
) -> Student:
    """Return one student or 404 when it does not exist."""
    return await service.get_by_id(student_id)
