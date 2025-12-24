"""Environment feedback device API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.environment_device import EnvironmentDeviceRepository
from app.db.repositories.environment_reading import EnvironmentReadingRepository
from app.db.session import get_session
from app.schemas.environment import (
    CurrentReadingsResponse,
    DEVICE_TYPES,
    DeviceCurrentReading,
    DeviceHistoryResponse,
    DeviceTypesResponse,
    EnvironmentDeviceCreate,
    EnvironmentDeviceListResponse,
    EnvironmentDeviceResponse,
    EnvironmentDeviceUpdate,
    EnvironmentReadingResponse,
    ReadingStatus,
    TemperatureUnit,
)
from app.services.environment.polling import get_polling_service

router = APIRouter(prefix="/environment", tags=["environment"])
logger = get_logger(__name__)


def convert_temperature(celsius: float | None, unit: str) -> float | None:
    """Convert temperature from Celsius to the specified unit."""
    if celsius is None:
        return None
    if unit == TemperatureUnit.FAHRENHEIT.value:
        return (celsius * 9 / 5) + 32
    return celsius


def convert_temperature_tolerance(tolerance: float | None, unit: str) -> float | None:
    """Convert temperature tolerance from Celsius to the specified unit.

    For Fahrenheit, multiply by 9/5 (no offset since it's a difference, not absolute).
    """
    if tolerance is None:
        return None
    if unit == TemperatureUnit.FAHRENHEIT.value:
        return tolerance * 9 / 5
    return tolerance


def calculate_status(
    current: float | None,
    target: float | None,
    tolerance: float | None,
) -> tuple[ReadingStatus, float | None]:
    """Calculate reading status and deviation from target.

    Returns:
        Tuple of (status, deviation)
        - status: normal, high, low, or unknown
        - deviation: how far from target (positive = above, negative = below)
    """
    if current is None or target is None:
        return ReadingStatus.UNKNOWN, None

    deviation = current - target
    tol = tolerance if tolerance is not None else 0

    if deviation > tol:
        return ReadingStatus.HIGH, deviation
    elif deviation < -tol:
        return ReadingStatus.LOW, deviation
    else:
        return ReadingStatus.NORMAL, deviation


@router.get("/device-types", response_model=DeviceTypesResponse)
async def get_device_types() -> DeviceTypesResponse:
    """Get available environment device types.

    Returns information about supported sensor types including
    what they measure and how to configure them.
    """
    return DeviceTypesResponse(device_types=DEVICE_TYPES)


@router.get("/devices", response_model=EnvironmentDeviceListResponse)
async def list_devices(
    session: Annotated[AsyncSession, Depends(get_session)],
    enabled_only: bool = False,
) -> EnvironmentDeviceListResponse:
    """List all configured environment devices.

    Args:
        enabled_only: If True, only return enabled devices
        session: Database session

    Returns:
        List of environment devices
    """
    repo = EnvironmentDeviceRepository(session)

    if enabled_only:
        devices = await repo.get_enabled()
    else:
        devices = await repo.get_all()

    logger.info("environment_devices_listed", count=len(devices))

    return EnvironmentDeviceListResponse(
        devices=[EnvironmentDeviceResponse.model_validate(d) for d in devices],
        total=len(devices),
    )


@router.get("/devices/{device_id}", response_model=EnvironmentDeviceResponse)
async def get_device(
    device_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EnvironmentDeviceResponse:
    """Get a specific environment device.

    Args:
        device_id: Device ID
        session: Database session

    Returns:
        Environment device details

    Raises:
        HTTPException: 404 if device not found
    """
    repo = EnvironmentDeviceRepository(session)
    device = await repo.get_by_id(device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment device {device_id} not found",
        )

    return EnvironmentDeviceResponse.model_validate(device)


@router.post(
    "/devices",
    response_model=EnvironmentDeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    device_data: EnvironmentDeviceCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EnvironmentDeviceResponse:
    """Create a new environment device.

    Args:
        device_data: Device configuration
        session: Database session

    Returns:
        Created device

    Raises:
        HTTPException: 409 if pin/address already in use
    """
    repo = EnvironmentDeviceRepository(session)

    # Check for duplicate pin/address
    existing = await repo.get_by_pin(device_data.pin_or_address)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pin/address '{device_data.pin_or_address}' is already assigned to device '{existing.name}'",
        )

    device = await repo.create(**device_data.model_dump())

    logger.info(
        "environment_device_created",
        device_id=device.id,
        name=device.name,
        device_type=device.device_type,
    )

    return EnvironmentDeviceResponse.model_validate(device)


@router.patch("/devices/{device_id}", response_model=EnvironmentDeviceResponse)
async def update_device(
    device_id: int,
    device_data: EnvironmentDeviceUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EnvironmentDeviceResponse:
    """Update an environment device.

    Args:
        device_id: Device ID
        device_data: Fields to update
        session: Database session

    Returns:
        Updated device

    Raises:
        HTTPException: 404 if device not found, 409 if pin/address conflict
    """
    repo = EnvironmentDeviceRepository(session)

    # Check device exists
    device = await repo.get_by_id(device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment device {device_id} not found",
        )

    # Check for pin/address conflict if updating
    if device_data.pin_or_address is not None:
        existing = await repo.get_by_pin(device_data.pin_or_address)
        if existing and existing.id != device_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pin/address '{device_data.pin_or_address}' is already assigned to device '{existing.name}'",
            )

    # Update device
    update_data = device_data.model_dump(exclude_unset=True)
    device = await repo.update(device_id, **update_data)

    logger.info(
        "environment_device_updated",
        device_id=device_id,
        updated_fields=list(update_data.keys()),
    )

    return EnvironmentDeviceResponse.model_validate(device)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete an environment device.

    Args:
        device_id: Device ID
        session: Database session

    Raises:
        HTTPException: 404 if device not found
    """
    repo = EnvironmentDeviceRepository(session)

    deleted = await repo.delete(device_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment device {device_id} not found",
        )

    logger.info("environment_device_deleted", device_id=device_id)


# ============================================================================
# Reading Endpoints
# ============================================================================


@router.get("/readings/current", response_model=CurrentReadingsResponse)
async def get_current_readings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentReadingsResponse:
    """Get current readings from all enabled devices.

    Returns the most recent reading for each enabled device,
    combining in-memory cache with database values.

    Returns:
        Current readings from all devices
    """
    device_repo = EnvironmentDeviceRepository(session)
    reading_repo = EnvironmentReadingRepository(session)
    polling_service = get_polling_service()

    # Get all devices (including disabled for completeness)
    devices = await device_repo.get_all()

    # Get latest readings from database
    db_readings = await reading_repo.get_latest_for_all_devices()
    db_readings_map = {r.device_id: r for r in db_readings}

    # Get in-memory readings (more current)
    cached_readings = polling_service.get_all_latest_readings()

    readings = []
    for device in devices:
        # Prefer cached reading, fall back to database
        cached = cached_readings.get(device.id)
        db_reading = db_readings_map.get(device.id)

        # Get raw values
        temp_celsius = cached.temperature if cached else (db_reading.temperature if db_reading else None)
        humidity = cached.humidity if cached else (db_reading.humidity if db_reading else None)
        pressure = cached.pressure if cached else (db_reading.pressure if db_reading else None)

        # Convert temperature based on device's unit preference
        temp_unit = getattr(device, 'temperature_unit', 'C')
        temp_display = convert_temperature(temp_celsius, temp_unit)

        # Get target values (temperature needs conversion)
        target_temp_celsius = getattr(device, 'target_temperature', None)
        target_temp_display = convert_temperature(target_temp_celsius, temp_unit)
        target_humidity = getattr(device, 'target_humidity', None)
        target_pressure = getattr(device, 'target_pressure', None)

        # Get tolerance values (temperature tolerance needs conversion)
        temp_tolerance_celsius = getattr(device, 'temperature_tolerance', None)
        temp_tolerance_display = convert_temperature_tolerance(temp_tolerance_celsius, temp_unit)
        humidity_tolerance = getattr(device, 'humidity_tolerance', None)
        pressure_tolerance = getattr(device, 'pressure_tolerance', None)

        # Calculate status and deviation for each measurement
        temp_status, temp_deviation = calculate_status(temp_display, target_temp_display, temp_tolerance_display)
        humidity_status, humidity_deviation = calculate_status(humidity, target_humidity, humidity_tolerance)
        pressure_status, pressure_deviation = calculate_status(pressure, target_pressure, pressure_tolerance)

        reading = DeviceCurrentReading(
            device_id=device.id,
            device_name=device.name,
            device_type=device.device_type,
            enabled=device.enabled,
            temperature_unit=TemperatureUnit(temp_unit),
            temperature=temp_display,
            humidity=humidity,
            pressure=pressure,
            target_temperature=target_temp_display,
            target_humidity=target_humidity,
            target_pressure=target_pressure,
            temperature_tolerance=temp_tolerance_display,
            humidity_tolerance=humidity_tolerance,
            pressure_tolerance=pressure_tolerance,
            temperature_status=temp_status,
            humidity_status=humidity_status,
            pressure_status=pressure_status,
            temperature_deviation=temp_deviation,
            humidity_deviation=humidity_deviation,
            pressure_deviation=pressure_deviation,
            timestamp=db_reading.timestamp if db_reading else None,
            error=cached.error if cached and cached.error else None,
        )
        readings.append(reading)

    return CurrentReadingsResponse(readings=readings, total=len(readings))


@router.get("/readings/{device_id}/current", response_model=DeviceCurrentReading)
async def get_device_current_reading(
    device_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DeviceCurrentReading:
    """Get current reading for a specific device.

    Args:
        device_id: Device ID
        session: Database session

    Returns:
        Current reading for the device

    Raises:
        HTTPException: 404 if device not found
    """
    device_repo = EnvironmentDeviceRepository(session)
    reading_repo = EnvironmentReadingRepository(session)
    polling_service = get_polling_service()

    device = await device_repo.get_by_id(device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment device {device_id} not found",
        )

    # Get latest reading from database
    db_reading = await reading_repo.get_latest_for_device(device_id)

    # Get in-memory reading (more current)
    cached = polling_service.get_latest_reading(device_id)

    # Get raw values
    temp_celsius = cached.temperature if cached else (db_reading.temperature if db_reading else None)
    humidity = cached.humidity if cached else (db_reading.humidity if db_reading else None)
    pressure = cached.pressure if cached else (db_reading.pressure if db_reading else None)

    # Convert temperature based on device's unit preference
    temp_unit = getattr(device, 'temperature_unit', 'C')
    temp_display = convert_temperature(temp_celsius, temp_unit)

    # Get target values (temperature needs conversion)
    target_temp_celsius = getattr(device, 'target_temperature', None)
    target_temp_display = convert_temperature(target_temp_celsius, temp_unit)
    target_humidity = getattr(device, 'target_humidity', None)
    target_pressure = getattr(device, 'target_pressure', None)

    # Get tolerance values (temperature tolerance needs conversion)
    temp_tolerance_celsius = getattr(device, 'temperature_tolerance', None)
    temp_tolerance_display = convert_temperature_tolerance(temp_tolerance_celsius, temp_unit)
    humidity_tolerance = getattr(device, 'humidity_tolerance', None)
    pressure_tolerance = getattr(device, 'pressure_tolerance', None)

    # Calculate status and deviation for each measurement
    temp_status, temp_deviation = calculate_status(temp_display, target_temp_display, temp_tolerance_display)
    humidity_status, humidity_deviation = calculate_status(humidity, target_humidity, humidity_tolerance)
    pressure_status, pressure_deviation = calculate_status(pressure, target_pressure, pressure_tolerance)

    return DeviceCurrentReading(
        device_id=device.id,
        device_name=device.name,
        device_type=device.device_type,
        enabled=device.enabled,
        temperature_unit=TemperatureUnit(temp_unit),
        temperature=temp_display,
        humidity=humidity,
        pressure=pressure,
        target_temperature=target_temp_display,
        target_humidity=target_humidity,
        target_pressure=target_pressure,
        temperature_tolerance=temp_tolerance_display,
        humidity_tolerance=humidity_tolerance,
        pressure_tolerance=pressure_tolerance,
        temperature_status=temp_status,
        humidity_status=humidity_status,
        pressure_status=pressure_status,
        temperature_deviation=temp_deviation,
        humidity_deviation=humidity_deviation,
        pressure_deviation=pressure_deviation,
        timestamp=db_reading.timestamp if db_reading else None,
        error=cached.error if cached and cached.error else None,
    )


@router.get("/readings/{device_id}/history", response_model=DeviceHistoryResponse)
async def get_device_history(
    device_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    limit: int = Query(500, ge=1, le=2000, description="Maximum readings to return"),
) -> DeviceHistoryResponse:
    """Get historical readings for a device.

    Args:
        device_id: Device ID
        session: Database session
        hours: Number of hours of history (1-168, default 24)
        limit: Maximum readings to return (1-2000, default 500)

    Returns:
        Historical readings for the device

    Raises:
        HTTPException: 404 if device not found
    """
    device_repo = EnvironmentDeviceRepository(session)
    reading_repo = EnvironmentReadingRepository(session)

    device = await device_repo.get_by_id(device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment device {device_id} not found",
        )

    readings = await reading_repo.get_history(device_id, hours=hours, limit=limit)

    # Get temperature unit for this device
    temp_unit = getattr(device, 'temperature_unit', 'C')

    # Convert temperature readings if needed
    converted_readings = []
    for r in readings:
        reading_response = EnvironmentReadingResponse.model_validate(r)
        # Convert temperature if unit is Fahrenheit
        if reading_response.temperature is not None and temp_unit == TemperatureUnit.FAHRENHEIT.value:
            reading_response.temperature = convert_temperature(reading_response.temperature, temp_unit)
        converted_readings.append(reading_response)

    return DeviceHistoryResponse(
        device_id=device.id,
        device_name=device.name,
        device_type=device.device_type,
        temperature_unit=TemperatureUnit(temp_unit),
        readings=converted_readings,
        total=len(readings),
    )
