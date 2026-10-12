from app.integrations.groups.base import GroupData, GroupProvider


class MockGroupProvider(GroupProvider):
    async def get_groups(self) -> list[GroupData]:
        return [GroupData(external_id="mock-group-1", name="261-001")]
