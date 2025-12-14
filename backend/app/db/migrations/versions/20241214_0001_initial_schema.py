"""Initial schema baseline.

This migration represents the initial database schema as of December 2024.
It uses the 'if not exists' approach to be safe for databases created via create_all().

Revision ID: 0001_initial
Revises:
Create Date: 2024-12-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create cameras table
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("device_path", sa.String(length=255), nullable=False),
        sa.Column("camera_type", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("default_settings", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_path"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_cameras_name", "cameras", ["name"], unique=False, if_not_exists=True
    )

    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("timelapse_config", sa.JSON(), nullable=True),
        sa.Column("timelapse_progress", sa.Integer(), nullable=True, default=0),
        sa.Column("timelapse_dir", sa.String(length=500), nullable=True),
        sa.Column("output_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_jobs_camera_id", "jobs", ["camera_id"], unique=False, if_not_exists=True
    )
    op.create_index(
        "ix_jobs_job_type", "jobs", ["job_type"], unique=False, if_not_exists=True
    )
    op.create_index(
        "ix_jobs_status", "jobs", ["status"], unique=False, if_not_exists=True
    )

    # Create output_configs table
    op.create_table(
        "output_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "recordings_path",
            sa.String(length=500),
            nullable=False,
            default="/var/lib/timemachine/media/recordings",
        ),
        sa.Column(
            "stills_path",
            sa.String(length=500),
            nullable=False,
            default="/var/lib/timemachine/media/stills",
        ),
        sa.Column(
            "timelapse_path",
            sa.String(length=500),
            nullable=False,
            default="/var/lib/timemachine/media/timelapse",
        ),
        sa.Column("retention_days", sa.Integer(), nullable=False, default=30),
        sa.Column("retention_max_gb", sa.Integer(), nullable=False, default=50),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # Create events table
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_events_event_type",
        "events",
        ["event_type"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_events_severity", "events", ["severity"], unique=False, if_not_exists=True
    )
    op.create_index(
        "ix_events_created_at",
        "events",
        ["created_at"],
        unique=False,
        if_not_exists=True,
    )

    # Create temperature_configs table
    op.create_table(
        "temperature_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("target_temp", sa.Float(), nullable=True),
        sa.Column("sensor_pin", sa.Integer(), nullable=True),
        sa.Column("heater_pin", sa.Integer(), nullable=True),
        sa.Column("cooler_pin", sa.Integer(), nullable=True),
        sa.Column("hysteresis", sa.Float(), nullable=False, default=1.0),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop all tables (reverse migration)."""
    op.drop_table("temperature_configs")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_severity", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_table("events")
    op.drop_table("output_configs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_index("ix_jobs_camera_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_cameras_name", table_name="cameras")
    op.drop_table("cameras")
