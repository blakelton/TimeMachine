"""Storage API endpoints for file management."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_session
from app.schemas.storage import (
    RetentionEnforceRequest,
    RetentionEnforceResponse,
    StorageListResponse,
    StorageStatsResponse,
    StoredFileResponse,
)
from app.services.storage import storage_service
from app.services.storage.service import FileType

router = APIRouter(prefix="/storage", tags=["storage"])
logger = get_logger(__name__)


def _file_to_response(file) -> StoredFileResponse:
    """Convert StoredFile to response schema."""
    return StoredFileResponse(
        file_id=file.file_id,
        filename=file.filename,
        file_type=file.file_type.value,
        size_bytes=file.size_bytes,
        size_display=file.size_display,
        created_at=file.created_at,
        camera_id=file.camera_id,
        download_url=f"/api/v1/storage/files/{file.file_id}",
    )


@router.get("/files", response_model=StorageListResponse)
async def list_files(
    file_type: Annotated[
        Optional[str],
        Query(description="Filter by type: recording, still, timelapse"),
    ] = None,
    camera_id: Annotated[
        Optional[int],
        Query(description="Filter by camera ID"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Maximum files to return"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of files to skip"),
    ] = 0,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> StorageListResponse:
    """List stored files with optional filtering.

    Files are sorted by creation time (newest first).

    Args:
        file_type: Filter by file type
        camera_id: Filter by camera ID
        limit: Maximum files to return (1-500)
        offset: Number of files to skip for pagination
        session: Database session

    Returns:
        List of stored files with pagination info
    """
    # Parse file type
    parsed_type = None
    if file_type:
        try:
            parsed_type = FileType(file_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type: {file_type}. Must be: recording, still, or timelapse",
            )

    # Get files
    files = await storage_service.list_files(
        file_type=parsed_type,
        camera_id=camera_id,
        limit=limit + 1,  # Get one extra to check if more exist
        offset=offset,
    )

    # Check if more files exist
    has_more = len(files) > limit
    if has_more:
        files = files[:limit]

    # Get total count (approximate for performance)
    all_files = await storage_service.list_files(
        file_type=parsed_type,
        camera_id=camera_id,
        limit=10000,
        offset=0,
    )
    total = len(all_files)

    logger.info(
        "storage_files_listed",
        file_type=file_type,
        camera_id=camera_id,
        count=len(files),
        total=total,
    )

    return StorageListResponse(
        files=[_file_to_response(f) for f in files],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> FileResponse:
    """Download a file by its secure ID.

    The file ID is validated to prevent path traversal attacks.

    Args:
        file_id: Secure file identifier
        session: Database session

    Returns:
        File download response

    Raises:
        HTTPException: 404 if file not found, 403 if access denied
    """
    # Validate and get file path
    file_path = storage_service.get_file_path(file_id)

    if file_path is None:
        # Check if it's an invalid ID or just missing file
        decoded = storage_service.decode_file_id(file_id)
        if decoded is None:
            logger.warning("storage_invalid_file_id", file_id=file_id[:30])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid file ID",
            )
        else:
            logger.warning("storage_file_not_found", file_id=file_id[:30])
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

    # Determine content type
    suffix = file_path.suffix.lower()
    content_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
    }
    content_type = content_type_map.get(suffix, "application/octet-stream")

    logger.info(
        "storage_file_downloaded",
        file_id=file_id[:30],
        filename=file_path.name,
        content_type=content_type,
    )

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=content_type,
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict:
    """Delete a file by its secure ID.

    Args:
        file_id: Secure file identifier
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if file not found, 403 if access denied
    """
    # Get file info first for logging
    file_info = storage_service.get_file(file_id)

    if file_info is None:
        decoded = storage_service.decode_file_id(file_id)
        if decoded is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid file ID",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Delete the file
    success = await storage_service.delete_file(file_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )

    logger.info(
        "storage_file_deleted_api",
        file_id=file_id[:30],
        filename=file_info.filename,
        size_mb=file_info.size_mb,
    )

    return {"message": "File deleted", "filename": file_info.filename}


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> StorageStatsResponse:
    """Get storage statistics.

    Returns file counts, sizes by type, and disk usage information.

    Args:
        session: Database session

    Returns:
        Storage statistics
    """
    stats = await storage_service.get_storage_stats()

    logger.info(
        "storage_stats_retrieved",
        total_files=stats["total_files"],
        total_size=stats["total_size_display"],
    )

    return StorageStatsResponse(**stats)


@router.post("/retention/enforce", response_model=RetentionEnforceResponse)
async def enforce_retention(
    request: RetentionEnforceRequest = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> RetentionEnforceResponse:
    """Manually trigger retention enforcement.

    Deletes files older than max_age_days and/or reduces total storage
    to under max_size_gb by deleting oldest files first.

    Args:
        request: Optional retention parameters (uses defaults if not provided)
        session: Database session

    Returns:
        Summary of deleted files
    """
    if request is None:
        request = RetentionEnforceRequest()

    results = await storage_service.enforce_retention(
        max_age_days=request.max_age_days,
        max_size_gb=request.max_size_gb,
    )

    logger.info(
        "storage_retention_enforced_api",
        deleted_by_age=results["deleted_by_age"],
        deleted_by_size=results["deleted_by_size"],
        deleted_size=results["deleted_size_display"],
    )

    return RetentionEnforceResponse(**results)
