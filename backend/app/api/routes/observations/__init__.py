"""Observation API routes package."""

from fastapi import APIRouter

from .batch import router as batch_router
from .crud import router as crud_router
from .lifecycle import router as lifecycle_router
from .media import router as media_router

router = APIRouter(prefix="/observations", tags=["observations"])

# Include all sub-routers
# Order matters: lifecycle operations first (no path params conflicts),
# then CRUD (general routes), then media (specific path params), then batch
router.include_router(lifecycle_router)
router.include_router(crud_router)
router.include_router(media_router)
router.include_router(batch_router)
