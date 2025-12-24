"""Camera preview endpoints."""

import asyncio
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.job import OperationResponse
from app.services.camera import preview_service
from app.services.camera.pipeline import PipelineState

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{camera_id}/preview/start", response_model=OperationResponse)
async def start_camera_preview(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    fps: int = 10,
) -> OperationResponse:
    """Start preview stream for a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        fps: Framerate for preview (1-30, default 10)

    Returns:
        Preview start status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_start_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Clamp FPS to valid range
    fps = max(1, min(30, fps))

    # Start preview
    success, message = await preview_service.start_preview(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        port=8080 + camera_id,
        fps=fps,
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            pid=preview_service.get_preview_pid(camera_id),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/preview/stop", response_model=OperationResponse)
async def stop_camera_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> OperationResponse:
    """Stop preview stream for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Preview stop status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_stop_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Stop preview
    success, message = await preview_service.stop_preview(camera_id)

    if success:
        return OperationResponse(success=True, message=message)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


@router.get("/{camera_id}/preview/status")
async def get_preview_status(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Get preview status for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Preview status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_status_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    state = preview_service.get_preview_state(camera_id)
    port = preview_service.get_preview_port(camera_id)

    return {
        "camera_id": camera_id,
        "state": state.value if state else "idle",
        "port": port,
        "url": f"http://localhost:{port}" if port else None,
    }


@router.get("/{camera_id}/preview/stream")
async def stream_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> StreamingResponse:
    """Stream MJPEG preview from camera.

    This endpoint proxies the GStreamer TCP socket stream to HTTP,
    converting the raw multipart stream to browser-compatible MJPEG.

    GStreamer's multipartmux outputs raw boundaries without MIME headers.
    Browsers expect proper multipart format with Content-Type headers.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        StreamingResponse with MJPEG content

    Raises:
        HTTPException: 404 if camera not found, 503 if preview not running
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_stream_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Check if preview is running
    port = preview_service.get_preview_port(camera_id)
    if port is None:
        logger.warning("preview_stream_not_running", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview not running. Start preview first.",
        )

    async def stream_generator() -> AsyncGenerator[bytes, None]:
        """Connect to GStreamer TCP socket and yield browser-compatible MJPEG."""
        reader = None
        writer = None
        boundary = b"--frame"
        frame_count = 0

        try:
            # Connect to GStreamer TCP server
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port),
                timeout=5.0,
            )
            logger.info(
                "preview_stream_connected",
                camera_id=camera_id,
                port=port,
            )

            # Buffer for accumulating data
            buffer = b""

            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break

                buffer += chunk

                # Process complete frames from buffer
                while True:
                    # Find JPEG start marker (FFD8)
                    jpeg_start = buffer.find(b'\xff\xd8')
                    if jpeg_start == -1:
                        # No JPEG start found, clear buffer except last byte
                        buffer = buffer[-1:] if buffer else b""
                        break

                    # Find JPEG end marker (FFD9) after start
                    jpeg_end = buffer.find(b'\xff\xd9', jpeg_start)
                    if jpeg_end == -1:
                        # JPEG not complete, keep buffer from jpeg_start
                        buffer = buffer[jpeg_start:]
                        break

                    # Extract complete JPEG frame
                    jpeg_data = buffer[jpeg_start:jpeg_end + 2]

                    # Output browser-compatible MJPEG frame
                    yield boundary + b"\r\n"
                    yield b"Content-Type: image/jpeg\r\n"
                    yield f"Content-Length: {len(jpeg_data)}\r\n".encode()
                    yield b"\r\n"
                    yield jpeg_data
                    yield b"\r\n"

                    frame_count += 1
                    if frame_count == 1:
                        logger.info("preview_stream_first_frame", camera_id=camera_id)

                    # Remove processed frame from buffer
                    buffer = buffer[jpeg_end + 2:]

        except asyncio.TimeoutError:
            logger.error(
                "preview_stream_connection_timeout",
                camera_id=camera_id,
                port=port,
            )
        except ConnectionRefusedError:
            logger.error(
                "preview_stream_connection_refused",
                camera_id=camera_id,
                port=port,
            )
        except Exception as e:
            logger.error(
                "preview_stream_error",
                camera_id=camera_id,
                error=str(e),
            )
        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
            logger.info(
                "preview_stream_disconnected",
                camera_id=camera_id,
                frames_sent=frame_count,
            )

    return StreamingResponse(
        stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )
