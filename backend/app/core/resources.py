"""Resource management for camera operations."""

import asyncio
from typing import Optional

from app.core.logging import get_logger
from app.services.system.stats import check_memory_available, check_disk_available

logger = get_logger(__name__)


class EncoderSemaphore:
    """Semaphore for H.264 encoder access.

    Raspberry Pi 3 has a single hardware H.264 encoder.
    This semaphore ensures only one recording uses it at a time.
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(1)
        self._current_owner: Optional[str] = None

    async def acquire(self, owner: str) -> bool:
        """Acquire the encoder semaphore.

        Args:
            owner: Identifier for the process acquiring the encoder

        Returns:
            True if acquired successfully
        """
        logger.info("encoder_acquire_requested", owner=owner)

        acquired = await self._semaphore.acquire()
        if acquired:
            self._current_owner = owner
            logger.info("encoder_acquired", owner=owner)
            return True

        return False

    def release(self, owner: str) -> None:
        """Release the encoder semaphore.

        Args:
            owner: Identifier for the process releasing the encoder
        """
        if self._current_owner == owner:
            self._semaphore.release()
            logger.info("encoder_released", owner=owner)
            self._current_owner = None
        else:
            logger.warning(
                "encoder_release_mismatch",
                owner=owner,
                current_owner=self._current_owner,
            )

    def is_available(self) -> bool:
        """Check if encoder is available.

        Returns:
            True if encoder is not currently in use
        """
        return self._semaphore._value > 0  # noqa: SLF001

    def current_owner(self) -> Optional[str]:
        """Get current encoder owner.

        Returns:
            Current owner identifier or None
        """
        return self._current_owner


# Global encoder semaphore instance
encoder_semaphore = EncoderSemaphore()


async def check_resources_available(
    operation: str, min_memory_mb: int = 100, min_disk_mb: int = 500
) -> tuple[bool, str]:
    """Check if system has sufficient resources for an operation.

    Args:
        operation: Operation name for logging
        min_memory_mb: Minimum required memory in MB
        min_disk_mb: Minimum required disk space in MB

    Returns:
        Tuple of (available: bool, reason: str)
    """
    # Check memory availability
    memory_ok, memory_available_mb = check_memory_available(min_memory_mb)

    if not memory_ok:
        reason = (
            f"Insufficient memory: {memory_available_mb}MB available, "
            f"{min_memory_mb}MB required"
        )
        logger.warning(
            "resource_check_failed",
            operation=operation,
            reason="insufficient_memory",
            available_mb=memory_available_mb,
            required_mb=min_memory_mb,
        )
        return False, reason

    # Check disk space availability
    disk_ok, disk_available_mb = check_disk_available(min_disk_mb)

    if not disk_ok:
        reason = (
            f"Insufficient disk space: {disk_available_mb}MB available, "
            f"{min_disk_mb}MB required"
        )
        logger.warning(
            "resource_check_failed",
            operation=operation,
            reason="insufficient_disk_space",
            available_mb=disk_available_mb,
            required_mb=min_disk_mb,
        )
        return False, reason

    logger.debug(
        "resource_check_passed",
        operation=operation,
        available_memory_mb=memory_available_mb,
        available_disk_mb=disk_available_mb,
    )

    return True, "Resources available"
