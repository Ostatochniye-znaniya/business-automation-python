from abc import ABC, abstractmethod

from pydantic import BaseModel


class DepartmentData(BaseModel):
    external_id: str
    name: str


class DepartmentProvider(ABC):
    @abstractmethod
    async def get_departments(self) -> list[DepartmentData]:
        """Read external records without persisting domain entities."""
        raise NotImplementedError
