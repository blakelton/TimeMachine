"""Background task for monitoring camera device path changes.

USB cameras can change device paths (/dev/videoN) when reconnected.
This service periodically checks if device paths have changed and
updates the database + restarts affected previews.
"""

import asyncio

import structlog

from app.db.repositories.camera import CameraRepository
from app.db.session import AsyncSessionLocal
from app.services.camera import preview_service
from app.services.camera.resolver import CameraResolver

logger = structlog.get_logger(__name__)

# Check every 30 seconds for device path changes
DEVICE_CHECK_INTERVAL_SECONDS = 30


async def camera_device_monitor_loop() -> None:
    """Periodically check for camera device path changes.

    When a USB camera is reconnected, its /dev/videoN path may change.
    This monitor resolves hardware_id to current device path and updates
    the database + restarts previews if needed.
    """
    logger.info("camera_device_monitor_started")

    # Wait a bit before first check to let startup complete
    await asyncio.sleep(10)

    while True:
        try:
            await check_and_update_device_paths()
        except Exception as e:
            logger.error("camera_device_monitor_error", error=str(e))

        await asyncio.sleep(DEVICE_CHECK_INTERVAL_SECONDS)


async def check_and_update_device_paths() -> dict:
    """Check all cameras and update device paths if changed.

    Returns:
        Summary of updates made
    """
    summary = {"checked": 0, "updated": 0, "previews_restarted": 0}

    async with AsyncSessionLocal() as session:
        repo = CameraRepository(session)
        cameras = await repo.get_all()

        for camera in cameras:
            if not camera.hardware_id:
                continue

            summary["checked"] += 1

            # Resolve current device path from hardware_id
            current_path = await CameraResolver.resolve_hardware_id(camera.hardware_id)

            if current_path and current_path != camera.device_path:
                old_path = camera.device_path

                # Update database
                await repo.update_device_path(camera.id, current_path)
                summary["updated"] += 1

                logger.info(
                    "camera_device_path_changed",
                    camera_id=camera.id,
                    camera_name=camera.name,
                    old_path=old_path,
                    new_path=current_path,
                )

                # Restart preview if it was running
                preview_state = preview_service.get_preview_state(camera.id)
                if preview_state and preview_state.get("state") == "running":
                    logger.info(
                        "restarting_preview_after_path_change",
                        camera_id=camera.id,
                    )
                    try:
                        # Stop old preview
                        await preview_service.stop_preview(camera.id)

                        # Update camera object with new path for restart
                        camera.device_path = current_path

                        # Restart preview with new path
                        await preview_service.start_preview(camera)
                        summary["previews_restarted"] += 1

                        logger.info(
                            "preview_restarted_after_path_change",
                            camera_id=camera.id,
                            new_path=current_path,
                        )
                    except Exception as e:
                        logger.error(
                            "preview_restart_failed",
                            camera_id=camera.id,
                            error=str(e),
                        )

        await session.commit()

    if summary["updated"] > 0:
        logger.info("device_path_check_complete", **summary)

    return summary
