"""GStreamer pipeline management with crash recovery."""

import asyncio
import signal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class PipelineState(str, Enum):
    """Pipeline state enumeration."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CRASHED = "crashed"


@dataclass
class PipelineConfig:
    """GStreamer pipeline configuration."""

    pipeline_cmd: str
    description: str
    camera_id: int
    restart_on_crash: bool = True
    max_restarts: int = 3
    restart_delay_seconds: int = 5


class ManagedPipeline:
    """Managed GStreamer pipeline with automatic crash recovery.

    Features:
    - Automatic crash detection and recovery
    - PID tracking for process management
    - Configurable restart limits
    - State management
    - Graceful shutdown
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.state = PipelineState.IDLE
        self.process: Optional[asyncio.subprocess.Process] = None
        self.pid: Optional[int] = None
        self.restart_count = 0
        self.started_at: Optional[datetime] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> bool:
        """Start the GStreamer pipeline.

        Returns:
            True if started successfully
        """
        if self.state in [PipelineState.RUNNING, PipelineState.STARTING]:
            logger.warning(
                "pipeline_already_running",
                camera_id=self.config.camera_id,
                description=self.config.description,
            )
            return False

        logger.info(
            "pipeline_starting",
            camera_id=self.config.camera_id,
            description=self.config.description,
            command=self.config.pipeline_cmd,
        )

        self.state = PipelineState.STARTING

        try:
            # Start the GStreamer pipeline process
            self.process = await asyncio.create_subprocess_shell(
                self.config.pipeline_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=lambda: signal.signal(signal.SIGTERM, signal.SIG_DFL),
            )

            self.pid = self.process.pid
            self.started_at = datetime.utcnow()
            self.state = PipelineState.RUNNING

            logger.info(
                "pipeline_started",
                camera_id=self.config.camera_id,
                description=self.config.description,
                pid=self.pid,
            )

            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_process())

            return True

        except Exception as e:
            logger.error(
                "pipeline_start_failed",
                camera_id=self.config.camera_id,
                description=self.config.description,
                error=str(e),
            )
            self.state = PipelineState.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the GStreamer pipeline gracefully.

        Returns:
            True if stopped successfully
        """
        if self.state not in [PipelineState.RUNNING, PipelineState.STARTING]:
            logger.warning(
                "pipeline_not_running",
                camera_id=self.config.camera_id,
                description=self.config.description,
                state=self.state,
            )
            return False

        logger.info(
            "pipeline_stopping",
            camera_id=self.config.camera_id,
            description=self.config.description,
            pid=self.pid,
        )

        self.state = PipelineState.STOPPING
        self._stop_event.set()

        try:
            if self.process:
                # Send SIGTERM for graceful shutdown
                self.process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if not responding
                    logger.warning(
                        "pipeline_force_kill",
                        camera_id=self.config.camera_id,
                        pid=self.pid,
                    )
                    self.process.kill()
                    await self.process.wait()

            # Cancel monitor task
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            self.state = PipelineState.STOPPED
            self.process = None
            self.pid = None

            logger.info(
                "pipeline_stopped",
                camera_id=self.config.camera_id,
                description=self.config.description,
            )

            return True

        except Exception as e:
            logger.error(
                "pipeline_stop_failed",
                camera_id=self.config.camera_id,
                description=self.config.description,
                error=str(e),
            )
            self.state = PipelineState.ERROR
            return False

    async def _monitor_process(self) -> None:
        """Monitor the pipeline process and handle crashes."""
        while not self._stop_event.is_set():
            try:
                if not self.process:
                    break

                # Wait for process to exit
                returncode = await self.process.wait()

                # If we reach here, process has exited
                if not self._stop_event.is_set():
                    # Unexpected exit (crash)
                    logger.error(
                        "pipeline_crashed",
                        camera_id=self.config.camera_id,
                        description=self.config.description,
                        pid=self.pid,
                        returncode=returncode,
                        restart_count=self.restart_count,
                    )

                    self.state = PipelineState.CRASHED

                    # Attempt restart if configured
                    if (
                        self.config.restart_on_crash
                        and self.restart_count < self.config.max_restarts
                    ):
                        logger.info(
                            "pipeline_restart_scheduled",
                            camera_id=self.config.camera_id,
                            description=self.config.description,
                            delay_seconds=self.config.restart_delay_seconds,
                        )

                        await asyncio.sleep(self.config.restart_delay_seconds)

                        self.restart_count += 1
                        self.process = None
                        self.pid = None

                        # Restart
                        await self.start()
                    else:
                        logger.error(
                            "pipeline_restart_limit_reached",
                            camera_id=self.config.camera_id,
                            description=self.config.description,
                            restart_count=self.restart_count,
                        )
                        self.state = PipelineState.ERROR
                        break

                break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "pipeline_monitor_error",
                    camera_id=self.config.camera_id,
                    description=self.config.description,
                    error=str(e),
                )
                await asyncio.sleep(1)

    def get_state(self) -> PipelineState:
        """Get current pipeline state.

        Returns:
            Current pipeline state
        """
        return self.state

    def get_pid(self) -> Optional[int]:
        """Get current pipeline PID.

        Returns:
            Process ID or None
        """
        return self.pid

    def get_uptime_seconds(self) -> Optional[float]:
        """Get pipeline uptime in seconds.

        Returns:
            Uptime in seconds or None if not running
        """
        if self.started_at and self.state == PipelineState.RUNNING:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None
