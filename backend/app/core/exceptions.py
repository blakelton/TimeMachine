"""Custom exception classes for TimeMachine."""

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppException):
    """Request validation failed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class UnauthorizedError(AppException):
    """Authentication required or failed."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            message=f"{resource} with ID '{identifier}' not found",
            code=f"{resource.upper()}_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": identifier},
        )


class ConflictError(AppException):
    """Resource conflict (e.g., busy, already exists)."""

    def __init__(
        self,
        message: str,
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=409,
            details=details,
        )


class CameraBusyError(ConflictError):
    """Camera is in use by another operation."""

    def __init__(self, camera_id: int, operation: str) -> None:
        super().__init__(
            message=f"Camera {camera_id} is busy with {operation}",
            code="CAMERA_BUSY",
            details={"camera_id": camera_id, "operation": operation},
        )


class RecordingLimitError(ConflictError):
    """Maximum concurrent recordings reached."""

    def __init__(self, max_recordings: int, active_cameras: list[int]) -> None:
        super().__init__(
            message=f"Maximum {max_recordings} concurrent recording(s) allowed",
            code="RECORDING_LIMIT",
            details={
                "max_recordings": max_recordings,
                "active_cameras": active_cameras,
            },
        )


class EncoderBusyError(ConflictError):
    """H.264 encoder is in use."""

    def __init__(self, current_user: str) -> None:
        super().__init__(
            message=f"H.264 encoder is busy: {current_user}",
            code="ENCODER_BUSY",
            details={"current_user": current_user},
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT",
            status_code=429,
            details={"retry_after": retry_after},
        )


class StorageError(AppException):
    """Storage-related error."""

    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=507,
            details=details,
        )


class InsufficientStorageError(StorageError):
    """Not enough disk space."""

    def __init__(self, path: str, required_mb: int, available_mb: int) -> None:
        super().__init__(
            message=f"Insufficient storage: {available_mb}MB available, {required_mb}MB required",
            code="INSUFFICIENT_STORAGE",
            details={
                "path": path,
                "required_mb": required_mb,
                "available_mb": available_mb,
            },
        )


class PathSecurityError(StorageError):
    """Path traversal or security violation."""

    def __init__(self, message: str = "Invalid path detected") -> None:
        super().__init__(
            message=message,
            code="PATH_SECURITY_ERROR",
            details={},
        )
        self.status_code = 403


class CameraError(AppException):
    """Camera-related error."""

    def __init__(
        self,
        message: str,
        code: str = "CAMERA_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class CameraDisconnectedError(CameraError):
    """Camera hardware not available."""

    def __init__(self, camera_id: int) -> None:
        super().__init__(
            message=f"Camera {camera_id} is disconnected",
            code="CAMERA_DISCONNECTED",
            status_code=503,
            details={"camera_id": camera_id},
        )


class PipelineError(CameraError):
    """GStreamer pipeline failed."""

    def __init__(self, message: str, pipeline_name: str) -> None:
        super().__init__(
            message=message,
            code="PIPELINE_ERROR",
            status_code=500,
            details={"pipeline": pipeline_name},
        )


class ConfigError(AppException):
    """Configuration error."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            status_code=500,
        )


class MemoryPressureError(AppException):
    """Insufficient memory available."""

    def __init__(self, available_mb: int, required_mb: int) -> None:
        super().__init__(
            message=f"Insufficient memory: {available_mb}MB available, {required_mb}MB required",
            code="MEMORY_PRESSURE",
            status_code=503,
            details={
                "available_mb": available_mb,
                "required_mb": required_mb,
            },
        )
