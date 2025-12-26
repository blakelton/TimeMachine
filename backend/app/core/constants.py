"""Application-wide constants.

This module centralizes magic numbers and configuration constants
to improve maintainability and reduce duplication.
"""

from enum import StrEnum


# =============================================================================
# STATUS ENUMS
# =============================================================================


class ObservationStatus(StrEnum):
    """Status values for observations (recordings, timelapses, captures).

    Lifecycle:
        RUNNING -> COMPLETED | FAILED | STOPPED
    """

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class JobStatus(StrEnum):
    """Status values for background jobs.

    Lifecycle:
        PENDING -> RUNNING -> COMPLETED | FAILED | INTERRUPTED
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

# =============================================================================
# TIMING CONSTANTS (seconds unless noted)
# =============================================================================

# Stats broadcasting interval
STATS_BROADCAST_INTERVAL_SECONDS = 2

# Rate limiting
DEFAULT_RATE_LIMIT_RETRY_AFTER_SECONDS = 60

# Database
DB_BUSY_TIMEOUT_MS = 5000

# Video processing
FFMPEG_TIMEOUT_SECONDS = 60

# Timelapse sleep interval when waiting for frames
TIMELAPSE_WAIT_INTERVAL_SECONDS = 30


# =============================================================================
# VIDEO DEFAULTS
# =============================================================================

# Default frames per second for recording and timelapse output
DEFAULT_FPS = 30
DEFAULT_OUTPUT_FPS = 30

# Maximum FPS allowed
MAX_FPS = 60

# Default timelapse interval between captures
DEFAULT_TIMELAPSE_INTERVAL_SECONDS = 60

# Default resolution for pipelines
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080


# =============================================================================
# STORAGE CONSTANTS
# =============================================================================

# Maximum number of files to list in storage queries
MAX_FILE_LIST_LIMIT = 10000

# Default retention period in days
DEFAULT_RETENTION_DAYS = 30

# Chunk size for reading video stream data (bytes)
STREAM_CHUNK_SIZE_BYTES = 65536

# File ID logging truncation length
FILE_ID_LOG_TRUNCATE_LENGTH = 30


# =============================================================================
# PREVIEW / OBSERVATION CONSTANTS
# =============================================================================

# Default max frames for preview video generation
DEFAULT_PREVIEW_MAX_FRAMES = 60


# =============================================================================
# TEMPERATURE CONSTANTS
# =============================================================================

# Valid temperature range (Celsius)
MIN_TEMPERATURE_CELSIUS = -20
MAX_TEMPERATURE_CELSIUS = 60
