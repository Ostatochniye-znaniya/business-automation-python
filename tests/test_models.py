from sqlalchemy.dialects import mysql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from app.db.base import Base, register_models


def test_models_and_foreign_keys():
    register_models()
    configure_mappers()
    assert len(Base.metadata.tables) == 9
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=mysql.dialect()))
        for foreign_key in table.foreign_keys:
            assert foreign_key.column is not None
