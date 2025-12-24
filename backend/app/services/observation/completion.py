"""Observation completion detection and analysis."""

from dataclasses import dataclass
from enum import Enum, auto


class CompletionReason(Enum):
    """Reasons an observation completed."""
    DURATION_REACHED = auto()      # Target time reached
    FRAMES_REACHED = auto()        # Target frame count reached
    PIPELINE_CRASHED = auto()      # Unexpected stop
    USER_STOPPED = auto()          # Manual stop


@dataclass
class CompletionResult:
    """Result of checking for observation completion."""
    completed: bool
    reason: CompletionReason | None
    actual_progress: int
    health_info: dict | None
    note: str | None
