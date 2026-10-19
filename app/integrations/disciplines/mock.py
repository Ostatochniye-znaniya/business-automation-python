from app.integrations.disciplines.base import DisciplineData, DisciplineProvider


class MockDisciplineProvider(DisciplineProvider):
    async def get_disciplines(self) -> list[DisciplineData]:
        return [DisciplineData(external_id="mock-discipline-1", name="Математика")]
