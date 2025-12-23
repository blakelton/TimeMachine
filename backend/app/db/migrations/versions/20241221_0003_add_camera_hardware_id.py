"""Add hardware_id column to cameras table for persistent identification.

USB cameras can have different /dev/videoN paths after reboots.
The hardware_id stores a stable identifier (by-path symlink for USB,
libcamera:N for CSI) that can be resolved to the current device path.

Revision ID: 0003_hardware_id
Revises: 0002_observations
Create Date: 2024-12-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_hardware_id"
down_revision: str = "0002_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add hardware_id column with unique index.

    Note: We keep the device_path unique constraint for now since SQLite
    makes it complex to drop. The hardware_id will be the preferred
    unique identifier going forward, and device_path conflicts are
    checked in application code.
    """
    # Check if hardware_id column already exists (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(cameras)"))
    columns = [row[1] for row in result.fetchall()]

    if "hardware_id" not in columns:
        # Add hardware_id column
        op.add_column(
            "cameras",
            sa.Column("hardware_id", sa.String(500), nullable=True),
        )

    # Create unique index for hardware_id (if not exists)
    op.create_index(
        "ix_cameras_hardware_id",
        "cameras",
        ["hardware_id"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove hardware_id column."""
    op.drop_index("ix_cameras_hardware_id", table_name="cameras")
    op.drop_column("cameras", "hardware_id")
