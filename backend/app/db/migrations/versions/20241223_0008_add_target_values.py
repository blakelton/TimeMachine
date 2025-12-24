"""Add target values and tolerances to environment_devices.

Revision ID: 0008_target_values
Revises: 0007_temperature_unit
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_target_values"
down_revision: str = "0007_temperature_unit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add target values and tolerance columns to environment_devices."""
    # Target values (stored in Celsius for temperature)
    op.add_column(
        "environment_devices",
        sa.Column("target_temperature", sa.Float(), nullable=True),
    )
    op.add_column(
        "environment_devices",
        sa.Column("target_humidity", sa.Float(), nullable=True),
    )
    op.add_column(
        "environment_devices",
        sa.Column("target_pressure", sa.Float(), nullable=True),
    )

    # Tolerance values (± range around target)
    op.add_column(
        "environment_devices",
        sa.Column("temperature_tolerance", sa.Float(), nullable=True, server_default="5.0"),
    )
    op.add_column(
        "environment_devices",
        sa.Column("humidity_tolerance", sa.Float(), nullable=True, server_default="10.0"),
    )
    op.add_column(
        "environment_devices",
        sa.Column("pressure_tolerance", sa.Float(), nullable=True, server_default="20.0"),
    )


def downgrade() -> None:
    """Remove target values and tolerance columns from environment_devices."""
    op.drop_column("environment_devices", "pressure_tolerance")
    op.drop_column("environment_devices", "humidity_tolerance")
    op.drop_column("environment_devices", "temperature_tolerance")
    op.drop_column("environment_devices", "target_pressure")
    op.drop_column("environment_devices", "target_humidity")
    op.drop_column("environment_devices", "target_temperature")
