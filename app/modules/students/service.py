from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate, StudentUpdate


class StudentService:
    """CRUD use cases for students."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_by_groups(self, group_ids: set[int]) -> dict[int, int]:
        from sqlalchemy import func

        return dict(
            (
                await self.session.execute(
                    select(Student.group_id, func.count(Student.id))
                    .where(Student.group_id.in_(group_ids))
                    .group_by(Student.group_id)
                )
            ).all()
        )

    async def get_by_id(self, student_id: int) -> Student:
        student = await self.session.get(Student, student_id)
        if student is None:
            raise NotFoundError("Student not found")
        return student

    async def list_students(
        self, group_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[Student]:
        statement = select(Student)
        if group_id is not None:
            statement = statement.where(Student.group_id == group_id)
        statement = statement.order_by(Student.full_name, Student.id).offset(offset).limit(limit)
        return list((await self.session.scalars(statement)).all())

    async def create_student(self, data: StudentCreate) -> Student:
        from app.modules.groups.service import GroupService

        await GroupService(self.session).get_by_id(data.group_id)
        student = Student(**data.model_dump())
        self.session.add(student)
        await self.session.commit()
        await self.session.refresh(student)
        return student

    async def update_student(self, student_id: int, data: StudentUpdate) -> Student:
        student = await self.get_by_id(student_id)
        from app.modules.groups.service import GroupService

        await GroupService(self.session).get_by_id(data.group_id)
        if student.group_id != data.group_id:
            from app.modules.results.service import ResultService

            if await ResultService(self.session).has_student_results(student.id):
                from app.core.exceptions import ConflictError

                raise ConflictError("Нельзя менять группу студента с сохранёнными результатами")
        for field, value in data.model_dump().items():
            setattr(student, field, value)
        await self.session.commit()
        await self.session.refresh(student)
        return student

    async def delete_student(self, student_id: int) -> None:
        student = await self.get_by_id(student_id)
        await self.session.delete(student)
        await self.session.commit()
