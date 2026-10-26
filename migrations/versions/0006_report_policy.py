"""Optional paper reports per testing period.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "testing_periods",
        sa.Column(
            "paper_reports_required", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.execute(
        "UPDATE reports SET final_status = CASE WHEN electronic_status = 'APPROVED' THEN 'COMPLETE' ELSE 'PENDING' END"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE reports SET final_status = CASE WHEN electronic_status = 'APPROVED' AND paper_status = 'APPROVED' THEN 'COMPLETE' ELSE 'PENDING' END"
    )
    op.drop_column("testing_periods", "paper_reports_required")
