"""Add dashboard preview settings to output_config table.

Adds settings to control live camera previews on the dashboard:
- dashboard_preview_enabled: Boolean to enable/disable live previews
- dashboard_preview_fps: Integer 0-30 for preview framerate (0 = static mode)

Revision ID: 0004_dashboard_preview
Revises: 0003_hardware_id
Create Date: 2024-12-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_dashboard_preview"
down_revision: str = "0003_hardware_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add dashboard preview settings columns."""
    # Check if columns already exist (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(output_configs)"))
    columns = [row[1] for row in result.fetchall()]

    if "dashboard_preview_enabled" not in columns:
        op.add_column(
            "output_configs",
            sa.Column(
                "dashboard_preview_enabled",
                sa.Boolean,
                nullable=False,
                server_default="1",
            ),
        )

    if "dashboard_preview_fps" not in columns:
        op.add_column(
            "output_configs",
            sa.Column(
                "dashboard_preview_fps",
                sa.Integer,
                nullable=False,
                server_default="10",
            ),
        )


def downgrade() -> None:
    """Remove dashboard preview settings columns."""
    op.drop_column("output_configs", "dashboard_preview_fps")
    op.drop_column("output_configs", "dashboard_preview_enabled")
