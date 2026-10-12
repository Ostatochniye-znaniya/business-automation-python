from app.integrations.employees.base import EmployeeData, EmployeeProvider


class MockEmployeeProvider(EmployeeProvider):
    async def get_employees(self) -> list[EmployeeData]:
        return [EmployeeData(external_id="mock-employee-1", full_name="Тестовый преподаватель")]
