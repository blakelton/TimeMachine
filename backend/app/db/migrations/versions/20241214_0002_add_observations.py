"""Add observations table.

This migration adds the observations table for the new unified
observation system (recordings and timelapses).

Revision ID: 0002_observations
Revises: 0001_initial
Create Date: 2024-12-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_observations"
down_revision: str = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create observations table."""
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.Integer(), nullable=False),
        sa.Column("observation_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("folder_path", sa.String(length=500), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("target_end_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folder_path"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_observations_camera_id",
        "observations",
        ["camera_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_observations_observation_type",
        "observations",
        ["observation_type"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_observations_status",
        "observations",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_observations_job_id",
        "observations",
        ["job_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop observations table."""
    op.drop_index("ix_observations_job_id", table_name="observations")
    op.drop_index("ix_observations_status", table_name="observations")
    op.drop_index("ix_observations_observation_type", table_name="observations")
    op.drop_index("ix_observations_camera_id", table_name="observations")
    op.drop_table("observations")
