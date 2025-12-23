"""Thumbnail generation service for observations."""

import asyncio
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Thumbnail settings
THUMBNAIL_WIDTH = 320
THUMBNAIL_HEIGHT = 180
THUMBNAIL_FILENAME = "thumbnail.jpg"


class ThumbnailService:
    """Service for generating and managing observation thumbnails.

    Supports generating thumbnails from:
    - Timelapse frames (uses middle frame or first available)
    - Video recordings (extracts frame via ffmpeg)
    - Still images (resizes via ffmpeg)
    """

    async def get_or_generate_thumbnail(
        self,
        observation_folder: Path,
        observation_type: str,
    ) -> Optional[Path]:
        """Get existing thumbnail or generate one if missing.

        Args:
            observation_folder: Path to observation folder
            observation_type: Type of observation (timelapse, recording, still)

        Returns:
            Path to thumbnail if available, None otherwise
        """
        thumbnail_path = observation_folder / THUMBNAIL_FILENAME

        # Return existing thumbnail
        if thumbnail_path.exists():
            return thumbnail_path

        # Try to generate thumbnail
        success = await self.generate_thumbnail(
            observation_folder, observation_type
        )

        if success and thumbnail_path.exists():
            return thumbnail_path

        return None

    async def generate_thumbnail(
        self,
        observation_folder: Path,
        observation_type: str,
    ) -> bool:
        """Generate a thumbnail for an observation.

        Args:
            observation_folder: Path to observation folder
            observation_type: Type of observation

        Returns:
            True if thumbnail was generated successfully
        """
        if observation_type == "timelapse":
            return await self._generate_timelapse_thumbnail(observation_folder)
        elif observation_type == "recording":
            return await self._generate_recording_thumbnail(observation_folder)
        elif observation_type == "still":
            return await self._generate_still_thumbnail(observation_folder)
        else:
            logger.warning(
                "unknown_observation_type_for_thumbnail",
                observation_type=observation_type,
            )
            return False

    async def _generate_timelapse_thumbnail(
        self,
        observation_folder: Path,
    ) -> bool:
        """Generate thumbnail from timelapse frames.

        Uses the middle frame for a representative preview.
        """
        frames_dir = observation_folder / "frames"
        if not frames_dir.exists():
            logger.warning("timelapse_frames_dir_not_found", folder=str(observation_folder))
            return False

        # Get sorted list of frames
        frames = sorted(frames_dir.glob("frame_*.jpg"))
        if not frames:
            # Try other image patterns
            frames = sorted(frames_dir.glob("*.jpg"))

        if not frames:
            logger.warning("no_frames_found_for_thumbnail", folder=str(observation_folder))
            return False

        # Use middle frame for representative preview
        middle_idx = len(frames) // 2
        source_frame = frames[middle_idx]

        return await self._resize_image_to_thumbnail(
            source_frame,
            observation_folder / THUMBNAIL_FILENAME,
        )

    async def _generate_recording_thumbnail(
        self,
        observation_folder: Path,
    ) -> bool:
        """Generate thumbnail from video recording.

        Extracts a frame from 1 second into the video.
        """
        # Look for output video file
        video_file = None
        for ext in [".mp4", ".mkv", ".avi", ".webm"]:
            candidate = observation_folder / f"output{ext}"
            if candidate.exists():
                video_file = candidate
                break

        # Also check for files starting with "output"
        if not video_file:
            for f in observation_folder.glob("output*"):
                if f.suffix in [".mp4", ".mkv", ".avi", ".webm"]:
                    video_file = f
                    break

        if not video_file:
            logger.warning("no_video_file_for_thumbnail", folder=str(observation_folder))
            return False

        return await self._extract_video_frame(
            video_file,
            observation_folder / THUMBNAIL_FILENAME,
            timestamp="00:00:01",
        )

    async def _generate_still_thumbnail(
        self,
        observation_folder: Path,
    ) -> bool:
        """Generate thumbnail from still image.

        Resizes the original image to thumbnail size.
        """
        # Look for image file in observation folder
        image_file = None
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            for f in observation_folder.glob(f"*{ext}"):
                # Skip the thumbnail itself
                if f.name == THUMBNAIL_FILENAME:
                    continue
                image_file = f
                break
            if image_file:
                break

        if not image_file:
            logger.warning("no_image_file_for_thumbnail", folder=str(observation_folder))
            return False

        return await self._resize_image_to_thumbnail(
            image_file,
            observation_folder / THUMBNAIL_FILENAME,
        )

    async def _resize_image_to_thumbnail(
        self,
        source: Path,
        destination: Path,
    ) -> bool:
        """Resize an image to thumbnail dimensions.

        Args:
            source: Source image path
            destination: Destination thumbnail path

        Returns:
            True if successful
        """
        cmd = (
            f"ffmpeg -y -i '{source}' "
            f"-vf 'scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black' "
            f"-frames:v 1 -q:v 2 '{destination}' 2>/dev/null"
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode == 0 and destination.exists():
                logger.info(
                    "thumbnail_generated",
                    source=str(source),
                    destination=str(destination),
                )
                return True
            else:
                logger.warning(
                    "thumbnail_generation_failed",
                    source=str(source),
                    returncode=proc.returncode,
                )
                return False

        except asyncio.TimeoutError:
            logger.error("thumbnail_generation_timeout", source=str(source))
            return False
        except Exception as e:
            logger.error("thumbnail_generation_error", source=str(source), error=str(e))
            return False

    async def _extract_video_frame(
        self,
        video_path: Path,
        destination: Path,
        timestamp: str = "00:00:01",
    ) -> bool:
        """Extract a frame from a video file.

        Args:
            video_path: Path to video file
            destination: Destination thumbnail path
            timestamp: Timestamp to extract frame from (HH:MM:SS)

        Returns:
            True if successful
        """
        cmd = (
            f"ffmpeg -y -ss {timestamp} -i '{video_path}' "
            f"-vf 'scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black' "
            f"-frames:v 1 -q:v 2 '{destination}' 2>/dev/null"
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode == 0 and destination.exists():
                logger.info(
                    "video_thumbnail_extracted",
                    video=str(video_path),
                    destination=str(destination),
                )
                return True
            else:
                # Try extracting from the very beginning if timestamp failed
                if timestamp != "00:00:00":
                    return await self._extract_video_frame(
                        video_path, destination, "00:00:00"
                    )
                logger.warning(
                    "video_thumbnail_extraction_failed",
                    video=str(video_path),
                    returncode=proc.returncode,
                )
                return False

        except asyncio.TimeoutError:
            logger.error("video_thumbnail_timeout", video=str(video_path))
            return False
        except Exception as e:
            logger.error("video_thumbnail_error", video=str(video_path), error=str(e))
            return False


# Global thumbnail service instance
thumbnail_service = ThumbnailService()
