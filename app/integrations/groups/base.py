from abc import ABC, abstractmethod

from pydantic import BaseModel


class GroupData(BaseModel):
    external_id: str
    name: str


class GroupProvider(ABC):
    @abstractmethod
    async def get_groups(self) -> list[GroupData]:
        """Read external records without persisting domain entities."""
        raise NotImplementedError
