"""Access management, orders, participation and scheduling agreement."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reports", sa.Column("previous_teacher_name", sa.String(255), nullable=True))
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("department_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("position", sa.String(255), nullable=True))
        batch.create_foreign_key("fk_user_department", "departments", ["department_id"], ["id"])
    op.add_column(
        "knowledge_tests",
        sa.Column("agreement_status", sa.String(16), nullable=False, server_default="PROPOSED"),
    )
    op.add_column("knowledge_tests", sa.Column("agreement_comment", sa.Text(), nullable=True))
    op.add_column("knowledge_tests", sa.Column("room", sa.String(100), nullable=True))
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("testing_periods.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("year", sa.String(9), nullable=False),
        sa.Column("semester", sa.String(16), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("draft", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_table(
        "group_participation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("study_groups.id"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("testing_periods.id"), nullable=False),
        sa.Column("participates", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.UniqueConstraint("group_id", "period_id", name="uq_participation"),
    )
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_role", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("processed_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("processed_at", sa.DateTime()),
    )
    op.create_index("ix_access_requests_user_id", "access_requests", ["user_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_table(
        "import_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
    )
    op.create_table(
        "dev_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_column("reports", "previous_teacher_name")
    for table in (
        "dev_sessions",
        "import_logs",
        "audit_events",
        "access_requests",
        "group_participation",
        "orders",
    ):
        op.drop_table(table)
    for column in ("room", "agreement_comment", "agreement_status"):
        op.drop_column("knowledge_tests", column)
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_user_department", type_="foreignkey")
        batch.drop_column("position")
        batch.drop_column("department_id")
