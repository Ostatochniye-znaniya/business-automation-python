from abc import ABC, abstractmethod

from pydantic import BaseModel


class StudentData(BaseModel):
    external_id: str
    full_name: str
    group_external_id: str


class StudentProvider(ABC):
    @abstractmethod
    async def get_students(self) -> list[StudentData]:
        """Read external records without persisting domain entities."""
        raise NotImplementedError
