from app.db.session import session_factory


async def test_session_lifecycle_without_database():
    async with session_factory() as session:
        assert not session.in_transaction()
