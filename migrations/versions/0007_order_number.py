"""Preserve the official order number separately from the database identifier."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("number", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "number")
