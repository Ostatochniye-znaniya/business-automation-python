from abc import ABC, abstractmethod

from pydantic import BaseModel


class EmployeeData(BaseModel):
    external_id: str
    full_name: str


class EmployeeProvider(ABC):
    @abstractmethod
    async def get_employees(self) -> list[EmployeeData]:
        """Read external records without persisting domain entities."""
        raise NotImplementedError
