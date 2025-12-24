# Plan: Refactor check_camera_health Function

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Current Complexity:** 32 (Grade E - CRITICAL)
**Target Complexity:** <10 per function (Grade A/B)
**File:** `backend/app/api/routes/cameras.py:232`

---

## Problem Statement

The `check_camera_health` function has a cyclomatic complexity of 32, far exceeding the recommended maximum of 10. This makes the function:
- Difficult to test comprehensively
- Hard to maintain and debug
- Prone to bugs when modifications are made
- Challenging for new developers to understand

## Current Structure Analysis

The function currently handles:
1. Database lookup for camera
2. Device existence check
3. Device accessibility check
4. CSI camera health checks (rpicam-hello, dmesg for I2C errors)
5. USB camera health checks (v4l2-ctl)
6. Error aggregation and response building

## Proposed Refactoring

### Strategy: Extract Helper Functions + Strategy Pattern

Split into focused, single-responsibility functions and use a strategy pattern for camera-type-specific checks.

### New Module Structure

Create a new module: `backend/app/services/camera/health.py`

```
backend/app/services/camera/
├── __init__.py
├── health.py          # NEW - Camera health checking service
├── capture.py
├── pipeline.py
├── preview.py
├── recording.py
└── timelapse.py
```

### Implementation Steps

#### Step 1: Create Health Check Service Module

Create `backend/app/services/camera/health.py` with:

```python
"""Camera health checking service."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a camera health check."""
    healthy: bool
    device_exists: bool
    device_accessible: bool
    error: str | None
    details: dict


class CameraHealthChecker(Protocol):
    """Protocol for camera-specific health checkers."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check camera health. Returns (error, details)."""
        ...


class CSIHealthChecker:
    """Health checker for CSI cameras."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check CSI camera using rpicam-hello and dmesg."""
        details: dict = {}
        error: str | None = None

        error, rpicam_details = await self._check_rpicam()
        details.update(rpicam_details)

        if not error:
            i2c_error, i2c_details = await self._check_i2c_errors()
            details.update(i2c_details)
            if i2c_error:
                error = i2c_error

        return error, details

    async def _check_rpicam(self) -> tuple[str | None, dict]:
        """Check rpicam-hello availability and camera detection."""
        # Implementation extracted from original
        ...

    async def _check_i2c_errors(self) -> tuple[str | None, dict]:
        """Check dmesg for I2C communication errors."""
        # Implementation extracted from original
        ...


class USBHealthChecker:
    """Health checker for USB cameras."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check USB camera using v4l2-ctl."""
        # Implementation extracted from original
        ...


async def check_device_exists(device_path: str) -> tuple[bool, dict]:
    """Check if device path exists."""
    exists = os.path.exists(device_path)
    return exists, {"device_exists": exists}


async def check_device_accessible(device_path: str) -> tuple[bool, dict]:
    """Check if device is readable."""
    details: dict = {}
    accessible = False
    try:
        accessible = os.access(device_path, os.R_OK)
        details["device_readable"] = accessible
    except Exception as e:
        details["access_error"] = str(e)
    return accessible, details


def get_health_checker(camera_type: str) -> CameraHealthChecker:
    """Factory function to get appropriate health checker."""
    checkers = {
        "csi": CSIHealthChecker(),
        "usb": USBHealthChecker(),
    }
    return checkers.get(camera_type, USBHealthChecker())


async def check_camera_health(
    device_path: str,
    camera_type: str,
) -> HealthCheckResult:
    """
    Check camera health and accessibility.

    This is the main entry point for health checks.
    Complexity: ~5 (down from 32)
    """
    details: dict = {}

    # Check device existence
    device_exists, exist_details = await check_device_exists(device_path)
    details.update(exist_details)

    # Check device accessibility
    device_accessible = False
    if device_exists:
        device_accessible, access_details = await check_device_accessible(device_path)
        details.update(access_details)

    # Run camera-type-specific checks
    error: str | None = None
    if device_exists and device_accessible:
        checker = get_health_checker(camera_type)
        error, type_details = await checker.check(device_path)
        details.update(type_details)
    elif not device_exists:
        error = f"Device {device_path} does not exist"
    elif not device_accessible:
        error = f"Device {device_path} is not accessible"

    healthy = device_exists and device_accessible and error is None

    return HealthCheckResult(
        healthy=healthy,
        device_exists=device_exists,
        device_accessible=device_accessible,
        error=error,
        details=details,
    )
```

#### Step 2: Update API Route

Simplify `cameras.py` route to use the new service:

```python
@router.get("/{camera_id}/health", response_model=CameraHealthResponse)
async def check_camera_health_endpoint(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)]
) -> CameraHealthResponse:
    """Check camera health and accessibility."""
    from app.services.camera.health import check_camera_health

    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    result = await check_camera_health(camera.device_path, camera.camera_type)

    logger.info(
        "camera_health_checked",
        camera_id=camera_id,
        healthy=result.healthy,
        error=result.error,
    )

    return CameraHealthResponse(
        camera_id=camera_id,
        name=camera.name,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        healthy=result.healthy,
        device_exists=result.device_exists,
        device_accessible=result.device_accessible,
        error=result.error,
        details=result.details if result.details else None,
    )
```

### Complexity Analysis After Refactor

| Function | Before | After |
|----------|--------|-------|
| `check_camera_health_endpoint` (route) | 32 | ~5 |
| `check_camera_health` (service) | - | ~5 |
| `CSIHealthChecker.check` | - | ~4 |
| `CSIHealthChecker._check_rpicam` | - | ~6 |
| `CSIHealthChecker._check_i2c_errors` | - | ~4 |
| `USBHealthChecker.check` | - | ~5 |
| `check_device_exists` | - | ~1 |
| `check_device_accessible` | - | ~2 |

**Total complexity distributed across 8 functions, each under 10.**

---

## Testing Strategy

### Unit Tests to Add

1. `test_check_device_exists` - Mock `os.path.exists`
2. `test_check_device_accessible` - Mock `os.access`
3. `test_csi_health_checker` - Mock subprocess calls
4. `test_usb_health_checker` - Mock subprocess calls
5. `test_get_health_checker_factory` - Verify correct checker returned
6. `test_check_camera_health_integration` - End-to-end with mocks

### Test File

Create `backend/tests/services/camera/test_health.py`

---

## Migration Steps

1. Create `backend/app/services/camera/health.py` with new implementation
2. Add unit tests for new module
3. Update `cameras.py` to use new service
4. Run existing tests to verify no regressions
5. Remove old inline code from route handler
6. Update `__init__.py` exports if needed

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Subprocess behavior changes | Keep subprocess calls identical, just moved |
| Missing error handling | Copy all try/except blocks exactly |
| Breaking API response | CameraHealthResponse schema unchanged |

---

## Success Criteria

- [ ] Route handler complexity < 10
- [ ] Each helper function complexity < 10
- [ ] All existing tests pass
- [ ] New unit tests added with >80% coverage
- [ ] API response format unchanged
- [ ] No performance regression

---

## Estimated Effort

- Implementation: 2-3 hours
- Testing: 1-2 hours
- Review & validation: 1 hour

**Total: ~4-6 hours**
