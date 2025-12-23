"""Temperature control API endpoints (stub for future implementation)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.db.session import get_session
from app.db.models.temperature_config import TemperatureConfig as TemperatureConfigModel
from app.models.schemas.temperature import (
    TemperatureConfig,
    TemperatureConfigCreate,
    TemperatureConfigUpdate,
    TemperatureReading,
    TemperatureStubMessage,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/temperature", tags=["temperature"])


@router.get("/stub", response_model=TemperatureStubMessage)
async def get_temperature_stub() -> TemperatureStubMessage:
    """
    Get stub message indicating temperature control is not yet implemented.

    This endpoint exists to maintain API compatibility for future temperature
    control features. The frontend can display this message to users.
    """
    return TemperatureStubMessage()


@router.get("/config", response_model=TemperatureConfig | None)
async def get_temperature_config(
    db: Annotated[AsyncSession, Depends(get_session)]
) -> TemperatureConfig | None:
    """
    Get current temperature configuration (stub).

    Returns configuration if it exists, or None if not configured.
    """
    from sqlalchemy import select

    result = await db.execute(select(TemperatureConfigModel))
    config = result.scalar_one_or_none()

    if config:
        return TemperatureConfig.model_validate(config)
    return None


@router.post("/config", response_model=TemperatureConfig, status_code=201)
async def create_temperature_config(
    config_data: TemperatureConfigCreate, db: Annotated[AsyncSession, Depends(get_session)]
) -> TemperatureConfig:
    """
    Create temperature configuration (stub).

    Note: This only stores configuration. Actual temperature control
    logic is not yet implemented.
    """
    from sqlalchemy import select

    # Check if config already exists
    result = await db.execute(select(TemperatureConfigModel))
    existing_config = result.scalar_one_or_none()

    if existing_config:
        raise HTTPException(
            status_code=409,
            detail="Temperature configuration already exists. Use PUT to update.",
        )

    # Create new config
    config = TemperatureConfigModel(**config_data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)

    logger.info(
        "temperature_config_created",
        config_id=config.id,
        enabled=config.enabled,
        target_temp=config.target_temp,
    )

    return TemperatureConfig.model_validate(config)


@router.put("/config", response_model=TemperatureConfig)
async def update_temperature_config(
    config_data: TemperatureConfigUpdate, db: Annotated[AsyncSession, Depends(get_session)]
) -> TemperatureConfig:
    """
    Update temperature configuration (stub).

    Note: This only updates configuration. Actual temperature control
    logic is not yet implemented.
    """
    from sqlalchemy import select

    result = await db.execute(select(TemperatureConfigModel))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=404, detail="Temperature configuration not found. Use POST to create."
        )

    # Update only provided fields
    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)

    logger.info(
        "temperature_config_updated",
        config_id=config.id,
        enabled=config.enabled,
        target_temp=config.target_temp,
    )

    return TemperatureConfig.model_validate(config)


@router.delete("/config", status_code=204)
async def delete_temperature_config(db: Annotated[AsyncSession, Depends(get_session)]) -> None:
    """Delete temperature configuration."""
    from sqlalchemy import select

    result = await db.execute(select(TemperatureConfigModel))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Temperature configuration not found")

    await db.delete(config)
    await db.commit()

    logger.info("temperature_config_deleted", config_id=config.id)


@router.get("/reading", response_model=TemperatureReading)
async def get_temperature_reading(
    db: Annotated[AsyncSession, Depends(get_session)]
) -> TemperatureReading:
    """
    Get current temperature reading (stub).

    Returns stub data since hardware integration is not yet implemented.
    """
    from sqlalchemy import select

    result = await db.execute(select(TemperatureConfigModel))
    config = result.scalar_one_or_none()

    return TemperatureReading(
        current_temp=None,  # Would read from sensor
        target_temp=config.target_temp if config else None,
        heater_active=False,  # Would read from GPIO
        cooler_active=False,  # Would read from GPIO
    )
