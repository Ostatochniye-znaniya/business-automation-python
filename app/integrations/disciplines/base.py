from abc import ABC, abstractmethod

from pydantic import BaseModel


class DisciplineData(BaseModel):
    external_id: str
    name: str


class DisciplineProvider(ABC):
    @abstractmethod
    async def get_disciplines(self) -> list[DisciplineData]:
        """Read external records without persisting domain entities."""
        raise NotImplementedError
