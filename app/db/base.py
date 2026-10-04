from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata; domain tables live in their modules."""


def register_models() -> None:
    """Import every domain table for Alembic and mapper configuration."""
    from importlib import import_module

    for module in (
        "users",
        "departments",
        "periods",
        "groups",
        "disciplines",
        "students",
        "testing",
        "results",
        "reports",
    ):
        import_module(f"app.modules.{module}.models")
