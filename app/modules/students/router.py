from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate, StudentRead, StudentUpdate
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


@router.post("", response_model=StudentRead, status_code=201)
async def create_student(
    data: StudentCreate,
    service: Annotated[StudentService, Depends(get_service)],
) -> Student:
    """Create a student and persist it."""
    return await service.create_student(data)


@router.put(
    "/{student_id}",
    response_model=StudentRead,
    responses={404: {"description": "Student not found"}},
)
async def update_student(
    student_id: Annotated[int, Path(gt=0)],
    data: StudentUpdate,
    service: Annotated[StudentService, Depends(get_service)],
) -> Student:
    """Update a student or return 404 when it does not exist."""
    return await service.update_student(student_id, data)


@router.delete(
    "/{student_id}",
    status_code=204,
    responses={404: {"description": "Student not found"}},
)
async def delete_student(
    student_id: Annotated[int, Path(gt=0)],
    service: Annotated[StudentService, Depends(get_service)],
) -> None:
    """Delete a student or return 404 when it does not exist."""
    await service.delete_student(student_id)
