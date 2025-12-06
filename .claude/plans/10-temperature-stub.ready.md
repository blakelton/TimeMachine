# Temperature Stub - Plan

## Overview

Create placeholder backend and UI for future temperature control functionality. No GPIO access - completely inert stub.

**Dependencies**: 02-database-config, 05-frontend-foundation
**Estimated Duration**: 0.5 days

---

## Phase 1: Backend Stub

### Goal
API endpoints that accept but don't apply temperature settings.

### Tasks

1. **Create `app/api/routes/temperature.py`**
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from datetime import datetime

   from app.db.session import get_session
   from app.models.schemas.temperature import (
       TemperatureConfigResponse,
       TemperatureConfigUpdate,
       TemperatureReadingResponse,
   )
   from app.models.schemas.common import ResponseWrapper, Meta

   router = APIRouter(prefix="/temperature")

   @router.get("", response_model=ResponseWrapper[TemperatureConfigResponse])
   async def get_temperature_config(session: AsyncSession = Depends(get_session)):
       """Get temperature control configuration (stub)."""
       # Return stub data - no actual implementation
       return ResponseWrapper(
           data=TemperatureConfigResponse(
               id=1,
               enabled=False,
               target_temp=None,
               sensor_pin=None,
               heater_pin=None,
               cooler_pin=None,
               hysteresis=1.0,
               is_implemented=False,  # Clear indicator this is a stub
               created_at=datetime.utcnow(),
               updated_at=datetime.utcnow(),
           ),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.put("", response_model=ResponseWrapper[TemperatureConfigResponse])
   async def update_temperature_config(
       data: TemperatureConfigUpdate,
       session: AsyncSession = Depends(get_session),
   ):
       """Update temperature config (stub - saves but doesn't apply)."""
       # TODO: When implementing, remove this stub
       # For now, just acknowledge the request but don't do anything
       return ResponseWrapper(
           data=TemperatureConfigResponse(
               id=1,
               enabled=False,  # Always disabled in stub
               target_temp=data.target_temp,
               sensor_pin=data.sensor_pin,
               heater_pin=data.heater_pin,
               cooler_pin=data.cooler_pin,
               hysteresis=data.hysteresis or 1.0,
               is_implemented=False,
               created_at=datetime.utcnow(),
               updated_at=datetime.utcnow(),
           ),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.get("/current", response_model=ResponseWrapper[TemperatureReadingResponse])
   async def get_current_temperature():
       """Get current temperature reading (stub - always unavailable)."""
       return ResponseWrapper(
           data=TemperatureReadingResponse(
               current_temp=None,
               is_available=False,
               message="Temperature sensor not configured",
           ),
           meta=Meta(timestamp=datetime.utcnow()),
       )
   ```

2. **Add router to main app**
   ```python
   from app.api.routes import temperature
   app.include_router(temperature.router, prefix="/api/v1", tags=["temperature"])
   ```

### Acceptance Criteria
- [ ] Endpoints return stub data
- [ ] No GPIO imports or access
- [ ] Clear "not implemented" indicators

---

## Phase 2: Data Models

### Goal
Define schemas ready for future implementation.

### Tasks

1. **Create `app/models/schemas/temperature.py`**
   ```python
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Optional

   class TemperatureConfigBase(BaseModel):
       enabled: bool = False
       target_temp: Optional[float] = Field(None, ge=-40, le=100)
       sensor_pin: Optional[int] = Field(None, ge=0, le=40)
       heater_pin: Optional[int] = Field(None, ge=0, le=40)
       cooler_pin: Optional[int] = Field(None, ge=0, le=40)
       hysteresis: float = Field(default=1.0, ge=0.1, le=10.0)

   class TemperatureConfigUpdate(BaseModel):
       enabled: Optional[bool] = None
       target_temp: Optional[float] = Field(None, ge=-40, le=100)
       sensor_pin: Optional[int] = Field(None, ge=0, le=40)
       heater_pin: Optional[int] = Field(None, ge=0, le=40)
       cooler_pin: Optional[int] = Field(None, ge=0, le=40)
       hysteresis: Optional[float] = Field(None, ge=0.1, le=10.0)

   class TemperatureConfigResponse(TemperatureConfigBase):
       id: int
       is_implemented: bool = False  # Indicates this is a stub
       created_at: datetime
       updated_at: datetime

       class Config:
           from_attributes = True

   class TemperatureReadingResponse(BaseModel):
       current_temp: Optional[float] = None
       is_available: bool = False
       message: Optional[str] = None
   ```

### Acceptance Criteria
- [ ] Schemas validate correctly
- [ ] Nullable fields for unset pins
- [ ] `is_implemented` flag present

---

## Phase 3: Frontend Stub

### Goal
Placeholder UI showing "Coming Soon".

### Tasks

1. **TemperaturePanel already created in 07-system-settings**
   - Shows "Coming Soon" banner
   - Disabled form preview
   - No actual functionality

### Acceptance Criteria
- [ ] Clear messaging to users
- [ ] Disabled controls visible
- [ ] No errors in console

---

## Phase 4: Extensibility Hooks

### Goal
Prepare codebase for future implementation.

### Tasks

1. **Create `app/services/temperature/__init__.py`**
   ```python
   """
   Temperature Control Service (Stub)
   
   TODO: Implementation requires:
   - GPIO library (RPi.GPIO or gpiozero)
   - Temperature sensor library (e.g., w1thermsensor for DS18B20)
   - Pin configuration
   - Control loop implementation
   
   Planned GPIO pins (to be confirmed):
   - Sensor: GPIO4 (1-Wire)
   - Heater relay: GPIO17
   - Cooler relay: GPIO27
   
   Implementation steps:
   1. Add GPIO dependencies to requirements.txt
   2. Create TemperatureService with control loop
   3. Add background task for monitoring
   4. Update API routes to use real service
   5. Remove is_implemented=False flags
   """
   
   from abc import ABC, abstractmethod
   from typing import Optional

   class TemperatureServiceProtocol(ABC):
       """Interface for temperature control service."""
       
       @abstractmethod
       async def get_current_temp(self) -> Optional[float]:
           """Read current temperature from sensor."""
           pass
       
       @abstractmethod
       async def set_target_temp(self, target: float) -> None:
           """Set target temperature."""
           pass
       
       @abstractmethod
       async def enable(self) -> bool:
           """Enable temperature control."""
           pass
       
       @abstractmethod
       async def disable(self) -> None:
           """Disable temperature control."""
           pass

   class TemperatureServiceStub(TemperatureServiceProtocol):
       """Stub implementation - does nothing."""
       
       async def get_current_temp(self) -> Optional[float]:
           return None
       
       async def set_target_temp(self, target: float) -> None:
           pass  # No-op
       
       async def enable(self) -> bool:
           return False  # Cannot enable stub
       
       async def disable(self) -> None:
           pass  # No-op

   # Default to stub
   temperature_service = TemperatureServiceStub()
   ```

2. **Add TODO markers in code**
   ```python
   # TODO(temperature): Replace stub with real implementation
   # See .claude/plans/10-temperature-stub.ready.md for details
   ```

### Acceptance Criteria
- [ ] Interface defined
- [ ] Stub implements interface
- [ ] Clear TODO documentation

---

## Phase 5: Testing

### Goal
Verify stub behavior without GPIO.

### Tasks

1. **Create `tests/unit/test_temperature_stub.py`**
   ```python
   import pytest
   from httpx import AsyncClient
   from app.main import app

   @pytest.mark.asyncio
   async def test_get_temperature_config():
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.get("/api/v1/temperature")
           assert response.status_code == 200
           data = response.json()["data"]
           assert data["is_implemented"] == False
           assert data["enabled"] == False

   @pytest.mark.asyncio
   async def test_get_current_temperature_unavailable():
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.get("/api/v1/temperature/current")
           assert response.status_code == 200
           data = response.json()["data"]
           assert data["is_available"] == False
           assert data["current_temp"] is None

   @pytest.mark.asyncio
   async def test_update_temperature_config_stays_disabled():
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.put(
               "/api/v1/temperature",
               json={"enabled": True, "target_temp": 25.0}
           )
           assert response.status_code == 200
           data = response.json()["data"]
           # Should stay disabled in stub
           assert data["enabled"] == False

   def test_no_gpio_imports():
       """Verify no GPIO libraries are imported in stub."""
       import ast
       import sys
       
       # Check that RPi.GPIO is not imported
       assert "RPi.GPIO" not in sys.modules
       assert "gpiozero" not in sys.modules
   ```

### Acceptance Criteria
- [ ] All stub tests pass
- [ ] No GPIO imports verified
- [ ] API behaves correctly

---

## Future Implementation Notes

When ready to implement temperature control:

1. **Hardware requirements**
   - DS18B20 temperature sensor
   - Relay module for heater/cooler
   - Wiring to GPIO pins

2. **Software requirements**
   ```bash
   pip install w1thermsensor RPi.GPIO
   ```

3. **Enable 1-Wire in `/boot/config.txt`**
   ```
   dtoverlay=w1-gpio,gpiopin=4
   ```

4. **Implementation checklist**
   - [ ] Create `TemperatureServiceReal` class
   - [ ] Add sensor reading with error handling
   - [ ] Implement PID or hysteresis control loop
   - [ ] Add background task for monitoring
   - [ ] Update API to use real service
   - [ ] Remove `is_implemented=False` flags
   - [ ] Add unit tests with mocked GPIO
   - [ ] Add integration tests on Pi hardware

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/10-temperature-stub.md`
