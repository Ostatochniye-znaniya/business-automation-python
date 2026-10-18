"""Testing lifecycle status and optional admission year for course display."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("study_groups", sa.Column("admission_year", sa.Integer(), nullable=True))
    op.add_column(
        "knowledge_tests",
        sa.Column(
            "status",
            sa.Enum("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="knowledgeteststatus"),
            nullable=False,
            server_default="PLANNED",
        ),
    )
    # No completion state can be inferred from an old scheduled date.
    op.alter_column(
        "knowledge_tests",
        "status",
        server_default=None,
        existing_type=sa.Enum(
            "PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="knowledgeteststatus"
        ),
    )


def downgrade():
    op.drop_column("knowledge_tests", "status")
    op.drop_column("study_groups", "admission_year")
