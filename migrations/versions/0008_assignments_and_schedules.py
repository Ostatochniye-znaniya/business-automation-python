"""Per-teacher assignments and faculty semester schedule review."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    assignments = op.create_table(
        "test_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "knowledge_test_id", sa.Integer(), sa.ForeignKey("knowledge_tests.id"), nullable=False
        ),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("scheduled_at", sa.DateTime()),
        sa.Column("agreement_status", sa.String(16), nullable=False),
        sa.Column("agreement_comment", sa.Text()),
        sa.UniqueConstraint("knowledge_test_id", "teacher_id", name="uq_test_teacher"),
    )
    op.create_index(
        "ix_test_assignments_knowledge_test_id", "test_assignments", ["knowledge_test_id"]
    )
    op.create_index("ix_test_assignments_teacher_id", "test_assignments", ["teacher_id"])
    # Keep historical instants/decisions verbatim. No date window restriction for old records.
    tests = sa.table(
        "knowledge_tests",
        *[
            sa.column(name)
            for name in (
                "id",
                "teacher_id",
                "scheduled_at",
                "agreement_status",
                "agreement_comment",
            )
        ],
    )
    op.execute(
        assignments.insert().from_select(
            [
                "knowledge_test_id",
                "teacher_id",
                "scheduled_at",
                "agreement_status",
                "agreement_comment",
            ],
            sa.select(
                tests.c.id,
                tests.c.teacher_id,
                tests.c.scheduled_at,
                tests.c.agreement_status,
                tests.c.agreement_comment,
            ).where(tests.c.teacher_id.is_not(None)),
        )
    )
    op.create_table(
        "faculty_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("testing_periods.id"), nullable=False),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.UniqueConstraint("faculty_id", "period_id", name="uq_faculty_schedule"),
    )


def downgrade():
    op.drop_table("faculty_schedules")
    op.drop_table("test_assignments")
