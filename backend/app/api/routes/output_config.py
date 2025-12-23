"""Output configuration API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.output_config import OutputConfigRepository
from app.db.session import get_session
from app.schemas.output_config import OutputConfigResponse, OutputConfigUpdate

router = APIRouter(prefix="/output-config", tags=["output-config"])
logger = get_logger(__name__)


@router.get("", response_model=OutputConfigResponse)
async def get_output_config(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OutputConfigResponse:
    """Get the current output configuration.

    If no configuration exists, creates and returns default configuration.

    Args:
        session: Database session

    Returns:
        Output configuration
    """
    repo = OutputConfigRepository(session)
    config = await repo.get_or_create_default()

    logger.info(
        "output_config_retrieved",
        config_id=config.id,
        recordings_path=config.recordings_path,
    )

    return OutputConfigResponse.model_validate(config)


@router.patch("", response_model=OutputConfigResponse)
async def update_output_config(
    config_data: OutputConfigUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OutputConfigResponse:
    """Update the output configuration.

    Args:
        config_data: Configuration update data
        session: Database session

    Returns:
        Updated output configuration
    """
    repo = OutputConfigRepository(session)

    # Get or create config
    config = await repo.get_or_create_default()

    # Update with provided fields
    update_data = config_data.model_dump(exclude_unset=True)
    updated_config = await repo.update(config.id, **update_data)

    logger.info("output_config_updated", config_id=config.id, updated_fields=update_data)

    return OutputConfigResponse.model_validate(updated_config)
