"""Exercise the actual migration against historical checks and report references."""

import importlib.util
from datetime import date, datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy.schema import CreateTable

from app.db.base import Base, register_models
from app.modules.departments.models import Department
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup
from app.modules.periods.models import TestingPeriod
from app.modules.reports.models import Report
from app.modules.testing.models import KnowledgeTest
from app.modules.testing.models import TestAssignment as Assignment
from app.modules.users.models import User


def test_assignment_backfill_and_downgrade():
    register_models()
    configure_mappers()
    assert len(Base.metadata.tables) == 21
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=mysql.dialect()))
        for fk in table.foreign_keys:
            assert fk.column is not None
    engine = create_engine("sqlite:///:memory:")
    old_tables = [
        t
        for t in Base.metadata.sorted_tables
        if t.name not in {"test_assignments", "faculty_schedules"}
    ]
    Base.metadata.create_all(engine, tables=old_tables)
    with Session(engine) as session:
        session.add(Department(id=1, name="Faculty", type="FACULTY"))
        session.add(User(id=1, full_name="Teacher", role="TEACHER"))
        session.add(Discipline(id=1, name="Math"))
        session.add(StudyGroup(id=1, name="Group"))
        session.add(
            TestingPeriod(
                id=1,
                name="Old",
                academic_year="2025/2026",
                semester=1,
                start_date=date(2025, 9, 1),
                end_date=date(2026, 1, 31),
                status="CLOSED",
            )
        )
        session.flush()
        # Core inserts intentionally avoid the new eager-loaded relationship before migration.
        session.execute(
            KnowledgeTest.__table__.insert(),
            [
                dict(
                    id=1,
                    period_id=1,
                    group_id=1,
                    discipline_id=1,
                    teacher_id=1,
                    status="COMPLETED",
                    scheduled_at=datetime(2025, 10, 1, 10),
                    agreement_status="AGREED",
                    agreement_comment="old comment",
                    room="101",
                )
            ],
        )
        session.add(
            Report(
                id=1,
                knowledge_test_id=1,
                electronic_status="APPROVED",
                electronic_file_key="old.pdf",
                final_status="COMPLETE",
            )
        )
        session.commit()
    path = Path("migrations/versions/0008_assignments_and_schedules.py")
    spec = importlib.util.spec_from_file_location("migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
    with Session(engine) as session:
        test = session.get(KnowledgeTest, 1)
        assert len(test.assignments) == 1
        assignment = test.assignments[0]
        assert assignment.teacher_id == 1
        assert assignment.scheduled_at == datetime(2025, 10, 1, 10)
        assert assignment.agreement_status == "AGREED"
        assert assignment.agreement_comment == "old comment"
        assert session.get(Report, 1).electronic_file_key == "old.pdf"
        scope = KnowledgeTest.assignments.any(Assignment.teacher_id == 1)
        assert session.scalar(select(KnowledgeTest).where(scope)).id == 1
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "test_assignments" not in inspect(conn).get_table_names()
        assert conn.execute(select(Report.electronic_file_key)).scalar() == "old.pdf"
