"""Live preview generation for timelapse observations."""

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.observation import ObservationRepository

logger = get_logger(__name__)


async def live_preview_loop(
    observation_id: int,
    folder_path: Path,
    output_fps: int,
) -> None:
    """Background loop that regenerates preview video from timelapse frames.

    Generates preview:
    1. After the first frame is captured
    2. Every output_fps frames thereafter (i.e., every "1 second of footage")

    Args:
        observation_id: Observation ID
        folder_path: Path to observation folder
        output_fps: Output video FPS - preview generated every fps frames
    """
    frames_dir = folder_path / "frames"
    preview_path = folder_path / "preview.mp4"
    last_preview_frame_count = 0
    first_preview_done = False

    # Poll every second to check for new frames
    poll_interval = 1.0

    while True:
        try:
            # Check how many frames we have
            frames = sorted(frames_dir.glob("frame_*.jpg"))
            frame_count = len(frames)

            should_generate = False

            # Generate initial preview after 2 frames (ffmpeg concat needs at least 2)
            if not first_preview_done and frame_count >= 2:
                should_generate = True
                first_preview_done = True
                logger.info(
                    "live_preview_initial",
                    observation_id=observation_id,
                    frame_count=frame_count,
                )

            # Generate preview every output_fps frames (1 second of footage)
            # e.g., at 15fps: generate at frames 15, 30, 45, etc.
            elif frame_count >= output_fps:
                # Calculate how many "seconds of footage" we have
                current_footage_seconds = frame_count // output_fps
                last_footage_seconds = last_preview_frame_count // output_fps

                if current_footage_seconds > last_footage_seconds:
                    should_generate = True
                    logger.info(
                        "live_preview_update",
                        observation_id=observation_id,
                        frame_count=frame_count,
                        footage_seconds=current_footage_seconds,
                    )

            if should_generate:
                # Use the last N seconds of footage for preview
                # Default to 5 seconds of preview video
                preview_seconds = 5
                max_frames = preview_seconds * output_fps
                success = await generate_quick_preview(
                    frames_dir, preview_path, frames, max_frames=max_frames, fps=output_fps
                )
                if success:
                    last_preview_frame_count = frame_count
                    logger.info(
                        "live_preview_generated",
                        observation_id=observation_id,
                        frame_count=frame_count,
                        preview_path=str(preview_path),
                    )
                else:
                    logger.warning(
                        "live_preview_generation_failed",
                        observation_id=observation_id,
                        frame_count=frame_count,
                    )

            await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.debug("live_preview_loop_cancelled", observation_id=observation_id)
            break
        except Exception as e:
            logger.warning(
                "live_preview_loop_error",
                observation_id=observation_id,
                error=str(e),
            )
            await asyncio.sleep(poll_interval)


async def generate_quick_preview(
    frames_dir: Path,
    preview_path: Path,
    frames: list,
    max_frames: int = 30,
    fps: int = 10,
) -> bool:
    """Generate a quick preview video from the latest frames.

    Uses the last N frames to create a short preview video.
    Optimized for speed over quality.

    Args:
        frames_dir: Directory containing frame images
        preview_path: Output path for preview video
        frames: Sorted list of frame files
        max_frames: Maximum frames to include
        fps: Output video FPS

    Returns:
        True if successful
    """
    # Use the last N frames for preview
    preview_frames = frames[-max_frames:] if len(frames) > max_frames else frames

    # Create temporary concat file
    concat_file = frames_dir / ".preview_frames.txt"
    temp_output = preview_path.with_suffix(".tmp.mp4")

    # Calculate duration per frame
    frame_duration = 1.0 / fps

    try:
        # Write frame list for ffmpeg concat demuxer with explicit duration
        with open(concat_file, "w") as f:
            for frame in preview_frames:
                f.write(f"file '{frame.name}'\n")
                f.write(f"duration {frame_duration}\n")
            # Add last file again without duration (concat demuxer quirk)
            if preview_frames:
                f.write(f"file '{preview_frames[-1].name}'\n")

        # Build fast ffmpeg command (ultrafast preset, low quality for speed)
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' "
            f"-vf 'scale=640:360:force_original_aspect_ratio=decrease,"
            f"pad=640:360:(ow-iw)/2:(oh-ih)/2' "
            f"-c:v libx264 -preset ultrafast -crf 35 "
            f"-pix_fmt yuv420p "
            f"-movflags +faststart "
            f"'{temp_output}'"
        )

        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(frames_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

        if proc.returncode == 0 and temp_output.exists():
            # Atomic rename to avoid partial reads
            temp_output.rename(preview_path)
            return True
        else:
            error_msg = stderr.decode()[:500] if stderr else "Unknown error"
            logger.warning(
                "quick_preview_ffmpeg_failed",
                returncode=proc.returncode,
                error=error_msg,
                frame_count=len(preview_frames),
            )
            if temp_output.exists():
                temp_output.unlink()
            return False

    except asyncio.TimeoutError:
        logger.warning("quick_preview_timeout")
        return False
    except Exception as e:
        logger.warning("quick_preview_error", error=str(e))
        return False
    finally:
        # Clean up temp files
        try:
            if concat_file.exists():
                concat_file.unlink()
            if temp_output.exists():
                temp_output.unlink()
        except Exception:
            pass


async def generate_timelapse_preview(
    observation_id: int,
    session: AsyncSession,
    max_frames: int = 60,
    fps: int = 10,
    resolution: tuple[int, int] = (640, 360),
) -> tuple[bool, str, str | None]:
    """Generate a preview video from timelapse frames.

    Creates a low-resolution preview video using the latest captured frames.
    This is useful for monitoring timelapse progress without waiting for
    the full video assembly.

    Args:
        observation_id: Observation ID
        session: Database session
        max_frames: Maximum frames to include (default 60 = 6s at 10fps)
        fps: Output video FPS (default 10)
        resolution: Output resolution as (width, height) (default 640x360)

    Returns:
        Tuple of (success, message, preview_path)
    """
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        return False, f"Observation {observation_id} not found", None

    if observation.observation_type != "timelapse":
        return False, "Preview generation only available for timelapses", None

    folder_path = Path(observation.folder_path)
    frames_dir = folder_path / "frames"

    if not frames_dir.exists():
        return False, "Frames directory not found", None

    # Get list of frame files sorted by name
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if len(frames) < 2:
        return False, "Not enough frames for preview (need at least 2)", None

    # Use the last N frames for preview
    preview_frames = frames[-max_frames:] if len(frames) > max_frames else frames
    preview_path = folder_path / "preview.mp4"

    # Build ffmpeg command for preview generation
    # Using a temporary file list for ffmpeg input
    concat_file = folder_path / "preview_frames.txt"

    # Calculate duration per frame
    frame_duration = 1.0 / fps

    try:
        # Write frame list for ffmpeg concat demuxer with explicit duration
        with open(concat_file, "w") as f:
            for frame in preview_frames:
                # Use relative path and escape single quotes
                f.write(f"file '{frame.name}'\n")
                f.write(f"duration {frame_duration}\n")
            # Add last file again without duration (concat demuxer quirk)
            if preview_frames:
                f.write(f"file '{preview_frames[-1].name}'\n")

        width, height = resolution
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' "
            f"-vf 'scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2' "
            f"-c:v libx264 -preset ultrafast -crf 28 "
            f"-pix_fmt yuv420p "
            f"-movflags +faststart "
            f"'{preview_path}'"
        )

        logger.info(
            "timelapse_preview_generating",
            observation_id=observation_id,
            frame_count=len(preview_frames),
            output=str(preview_path),
        )

        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(frames_dir),  # Run in frames directory for relative paths
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)

        if proc.returncode == 0 and preview_path.exists():
            file_size_kb = preview_path.stat().st_size / 1024
            logger.info(
                "timelapse_preview_success",
                observation_id=observation_id,
                output=str(preview_path),
                size_kb=file_size_kb,
            )
            return True, "Preview generated", str(preview_path)
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(
                "timelapse_preview_failed",
                observation_id=observation_id,
                returncode=proc.returncode,
                error=error_msg,
            )
            return False, f"Preview generation failed: {error_msg[:200]}", None

    except asyncio.TimeoutError:
        logger.error("timelapse_preview_timeout", observation_id=observation_id)
        return False, "Preview generation timed out", None
    except Exception as e:
        logger.error(
            "timelapse_preview_exception",
            observation_id=observation_id,
            error=str(e),
        )
        return False, f"Preview error: {str(e)}", None
    finally:
        # Clean up temporary file
        try:
            if concat_file.exists():
                concat_file.unlink()
        except Exception:
            pass
