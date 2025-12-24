"""Add environment_readings table.

Revision ID: 0006_environment_readings
Revises: 0005_environment_devices
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_environment_readings"
down_revision: str = "0005_environment_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create environment_readings table."""
    op.create_table(
        "environment_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["environment_devices.id"],
            ondelete="CASCADE",
        ),
    )
    # Create indexes for efficient querying
    op.create_index(
        "ix_environment_readings_device_timestamp",
        "environment_readings",
        ["device_id", "timestamp"],
    )
    op.create_index(
        "ix_environment_readings_timestamp",
        "environment_readings",
        ["timestamp"],
    )


def downgrade() -> None:
    """Drop environment_readings table."""
    op.drop_index("ix_environment_readings_timestamp", "environment_readings")
    op.drop_index("ix_environment_readings_device_timestamp", "environment_readings")
    op.drop_table("environment_readings")
