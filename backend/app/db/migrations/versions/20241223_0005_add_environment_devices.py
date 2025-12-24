"""Add environment_devices table.

Revision ID: 0005
Revises: 0004
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_environment_devices"
down_revision: str = "0004_dashboard_preview"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create environment_devices table."""
    op.create_table(
        "environment_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("pin_or_address", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False, default=30),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop environment_devices table."""
    op.drop_table("environment_devices")
