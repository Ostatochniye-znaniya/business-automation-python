"""Server-side bootstrap command; does not expose an unauthenticated API."""

import argparse
import asyncio

from sqlalchemy import select

from app.core.enums import UserRole
from app.db.base import register_models
from app.db.session import engine, session_factory
from app.modules.users.models import User


async def bootstrap(external_id: str, full_name: str) -> None:
    register_models()
    try:
        async with session_factory() as session:
            existing = await session.scalar(select(User).where(User.external_id == external_id))
            if existing:
                raise ValueError("Сотрудник с таким внешним идентификатором уже существует")
            actor = User(
                external_id=external_id, full_name=full_name, role=UserRole.ADMIN, is_active=True
            )
            session.add(actor)
            await session.commit()
            print(f"Создан администратор: id={actor.id}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создать первого администратора на сервере")
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    asyncio.run(bootstrap(args.external_id, args.name))
