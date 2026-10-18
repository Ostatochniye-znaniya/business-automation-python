"""Group recommendations and append-only change history."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "group_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("study_groups.id"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("testing_periods.id"), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("group_id", "period_id", name="uq_recommendation_group_period"),
    )
    op.create_index("ix_group_recommendations_group_id", "group_recommendations", ["group_id"])
    op.create_index("ix_group_recommendations_period_id", "group_recommendations", ["period_id"])
    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.Integer(),
            sa.ForeignKey("group_recommendations.id"),
            nullable=False,
        ),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_recommendation_history_recommendation_id",
        "recommendation_history",
        ["recommendation_id"],
    )


def downgrade():
    op.drop_table("recommendation_history")
    op.drop_table("group_recommendations")
