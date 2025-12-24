"""Camera API routes package."""

from fastapi import APIRouter

from .capture import router as capture_router
from .crud import router as crud_router
from .dashboard import router as dashboard_router
from .discovery import router as discovery_router
from .health import router as health_router
from .preview import router as preview_router
from .recording import router as recording_router
from .timelapse import router as timelapse_router

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Include all sub-routers
# Order matters: dashboard and discovery first (no path params),
# then CRUD (conflicts with path params), then feature routers
router.include_router(dashboard_router)
router.include_router(discovery_router)
router.include_router(crud_router)
router.include_router(health_router)
router.include_router(preview_router)
router.include_router(recording_router)
router.include_router(timelapse_router)
router.include_router(capture_router)
