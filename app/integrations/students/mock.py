from app.integrations.students.base import StudentData, StudentProvider


class MockStudentProvider(StudentProvider):
    async def get_students(self) -> list[StudentData]:
        return [
            StudentData(
                external_id="mock-student-1",
                full_name="Тестовый студент",
                group_external_id="mock-group-1",
            )
        ]
