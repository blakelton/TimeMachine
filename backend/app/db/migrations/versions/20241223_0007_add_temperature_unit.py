"""Add temperature_unit to environment_devices.

Revision ID: 0007_temperature_unit
Revises: 0006_environment_readings
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_temperature_unit"
down_revision: str = "0006_environment_readings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add temperature_unit column to environment_devices."""
    op.add_column(
        "environment_devices",
        sa.Column("temperature_unit", sa.String(length=1), nullable=False, server_default="C"),
    )


def downgrade() -> None:
    """Remove temperature_unit column from environment_devices."""
    op.drop_column("environment_devices", "temperature_unit")
