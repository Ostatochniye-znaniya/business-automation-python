from app.integrations.departments.base import DepartmentData, DepartmentProvider


class MockDepartmentProvider(DepartmentProvider):
    async def get_departments(self) -> list[DepartmentData]:
        return [DepartmentData(external_id="mock-department-1", name="Тестовая кафедра")]
