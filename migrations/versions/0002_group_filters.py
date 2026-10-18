"""Study programs and group enrollment by testing period."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(32), nullable=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
    )
    op.create_index("ix_study_programs_faculty_id", "study_programs", ["faculty_id"])
    op.add_column("study_groups", sa.Column("study_program_id", sa.Integer(), nullable=True))
    op.create_index("ix_study_groups_study_program_id", "study_groups", ["study_program_id"])
    op.create_foreign_key(
        "fk_study_groups_study_program",
        "study_groups",
        "study_programs",
        ["study_program_id"],
        ["id"],
    )
    op.create_table(
        "group_periods",
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("study_groups.id"), primary_key=True),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("testing_periods.id"), primary_key=True),
    )
    # Preserve the known enrollment of existing groups; untested groups are imported separately.
    op.execute(
        "INSERT INTO group_periods (group_id, period_id) SELECT DISTINCT group_id, period_id FROM knowledge_tests"
    )


def downgrade():
    op.drop_table("group_periods")
    op.drop_constraint("fk_study_groups_study_program", "study_groups", type_="foreignkey")
    op.drop_index("ix_study_groups_study_program_id", table_name="study_groups")
    op.drop_column("study_groups", "study_program_id")
    op.drop_index("ix_study_programs_faculty_id", table_name="study_programs")
    op.drop_table("study_programs")
