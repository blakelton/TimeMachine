"""Video assembly utilities for timelapse."""

import asyncio
from pathlib import Path

from app.core.logging import get_logger
from app.core.resources import encoder_semaphore

logger = get_logger(__name__)


async def assemble_video(
    timelapse_dir: Path,
    fps: int,
    camera_id: int,
) -> str | None:
    """Assemble timelapse frames into video using ffmpeg.

    Args:
        timelapse_dir: Directory containing frame images
        fps: Output video frames per second
        camera_id: Camera ID for logging

    Returns:
        Output video path or None on failure
    """
    # Check for ffmpeg
    output_file = timelapse_dir.parent / f"{timelapse_dir.name}.mp4"

    # Acquire encoder for assembly
    owner_id = f"camera_{camera_id}_timelapse_assembly"
    acquired = await encoder_semaphore.acquire(owner_id)

    if not acquired:
        logger.warning(
            "timelapse_assembly_encoder_busy",
            camera_id=camera_id,
            current_owner=encoder_semaphore.current_owner(),
        )
        return None

    try:
        # Build ffmpeg command for image sequence to video
        # Using glob pattern for frame files
        cmd = (
            f"ffmpeg -y -framerate {fps} "
            f"-pattern_type glob -i '{timelapse_dir}/frame_*.jpg' "
            f"-c:v libx264 -preset medium -crf 23 "
            f"-pix_fmt yuv420p "
            f"'{output_file}'"
        )

        logger.info(
            "timelapse_assembly_starting",
            camera_id=camera_id,
            input_dir=str(timelapse_dir),
            output=str(output_file),
            fps=fps,
        )

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600.0)

        if proc.returncode == 0 and output_file.exists():
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(
                "timelapse_assembly_success",
                camera_id=camera_id,
                output=str(output_file),
                size_mb=file_size_mb,
            )
            return str(output_file)
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(
                "timelapse_assembly_failed",
                camera_id=camera_id,
                returncode=proc.returncode,
                error=error_msg,
            )
            return None

    except asyncio.TimeoutError:
        logger.error("timelapse_assembly_timeout", camera_id=camera_id)
        return None
    except Exception as e:
        logger.error("timelapse_assembly_exception", camera_id=camera_id, error=str(e))
        return None
    finally:
        encoder_semaphore.release(owner_id)


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
