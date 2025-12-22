# Phase 2: Temperature Control

> Implement temperature control via relay/heater/cooler

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: Phase 1 (Temperature Monitoring)

---

## Objective

Implement active temperature control using relay-controlled heating/cooling devices. Enable users to maintain chamber temperature at a setpoint with configurable modes, alerts, and safety limits.

## Prerequisites

- [ ] Phase 1 complete (temperature monitoring working)
- [ ] Relay module available for testing
- [ ] Heating/cooling device for testing
- [ ] GPIO pins available for relay control

## Hardware

**Relay Module**: Standard 5V relay module
- Typically uses GPIO high/low for on/off control
- Isolation recommended between Pi and high-power devices
- SSR (Solid State Relay) preferred for frequent switching

**Typical Setup**:
- Relay IN → GPIO17 (configurable)
- Relay VCC → 5V
- Relay GND → Ground
- Relay NO/NC → Heater/Cooler

---

## Deliverables

### 1. Backend: Relay Control Service

**Purpose**: Control GPIO output for relay switching

**Tasks**:
- [ ] Create `backend/app/services/temperature/relay.py`
- [ ] Implement GPIO output control with RPi.GPIO or gpiozero
- [ ] Add safety limits (max on-time, cooldown period)
- [ ] Implement dual-relay support (heat + cool)
- [ ] Add relay state persistence on restart
- [ ] Create mock mode for development

**Interface**:
```python
class RelayService:
    async def set_state(relay_id: str, on: bool) -> None
    async def get_state(relay_id: str) -> bool
    async def configure(relay_id: str, gpio_pin: int, active_high: bool) -> None
```

**Files**:
- `backend/app/services/temperature/relay.py` (new)

---

### 2. Backend: Temperature Controller

**Purpose**: Control logic for maintaining setpoint

**Tasks**:
- [ ] Create `backend/app/services/temperature/controller.py`
- [ ] Implement control modes: OFF, HEAT, COOL, AUTO
- [ ] Implement hysteresis-based control (simple on/off with deadband)
- [ ] Optional: Implement PID control for smoother operation
- [ ] Add minimum cycle time to protect equipment
- [ ] Add anti-short-cycle protection
- [ ] Log control actions for debugging

**Control Logic**:
```
HEAT mode:
  if temp < setpoint - hysteresis: heater ON
  if temp > setpoint + hysteresis: heater OFF

COOL mode:
  if temp > setpoint + hysteresis: cooler ON
  if temp < setpoint - hysteresis: cooler OFF

AUTO mode:
  Use HEAT logic when below setpoint
  Use COOL logic when above setpoint
  Never run both simultaneously
```

**Interface**:
```python
class TemperatureController:
    async def set_mode(mode: ControlMode) -> None
    async def set_setpoint(temp_c: float) -> None
    async def set_hysteresis(degrees: float) -> None
    async def get_status() -> ControllerStatus
    async def process_reading(reading: TempReading) -> None
```

**Files**:
- `backend/app/services/temperature/controller.py` (new)

---

### 3. Backend: Database Extensions

**Purpose**: Store control configuration and history

**Tasks**:
- [ ] Extend TemperatureConfig with control settings
- [ ] Create ControlEvent model for logging
- [ ] Add relay configuration to database

**Schema Extensions**:
```python
class TemperatureConfig:
    # ... existing fields ...
    control_mode: str  # "off" | "heat" | "cool" | "auto"
    setpoint_c: float
    hysteresis_c: float
    heater_gpio: int | None
    cooler_gpio: int | None
    min_cycle_seconds: int
    max_runtime_minutes: int

class ControlEvent:
    id: int
    timestamp: datetime
    event_type: str  # "heater_on", "heater_off", "cooler_on", etc.
    trigger: str  # "setpoint", "limit", "manual", "timeout"
    temperature_c: float
    setpoint_c: float
```

**Files**:
- `backend/app/db/models/temperature.py` (extend)
- `backend/app/db/repositories/temperature.py` (extend)

---

### 4. Backend: API Extensions

**Purpose**: Control endpoints

**Endpoints**:
```
POST /api/v1/temperature/control/mode      → Set control mode
POST /api/v1/temperature/control/setpoint  → Set target temperature
GET  /api/v1/temperature/control/status    → Current controller status
GET  /api/v1/temperature/control/events    → Control event history
POST /api/v1/temperature/relay/{id}/set    → Manual relay control (override)
```

**Tasks**:
- [ ] Add control endpoints to temperature router
- [ ] Add relay manual control endpoints
- [ ] Add safety validation (limits, conflicts)
- [ ] Update OpenAPI schema

**Files**:
- `backend/app/api/routes/temperature.py` (extend)
- `backend/app/schemas/temperature.py` (extend)

---

### 5. Backend: Alert System

**Purpose**: Notifications for temperature events

**Tasks**:
- [ ] Create alert thresholds configuration
- [ ] Implement alert conditions:
  - Temperature above high limit
  - Temperature below low limit
  - Sensor failure
  - Heater/cooler runtime exceeded
- [ ] Create alert event model
- [ ] Integrate with WebSocket for real-time alerts
- [ ] Integrate with notification system (Phase 5)

**Files**:
- `backend/app/services/temperature/alerts.py` (new)
- `backend/app/db/models/alerts.py` (new)

---

### 6. Frontend: Control Panel

**Purpose**: UI for temperature control

**Tasks**:
- [ ] Create `TemperatureControl.tsx` component
- [ ] Add mode selector (OFF/HEAT/COOL/AUTO)
- [ ] Add setpoint input with +/- buttons
- [ ] Show current status (heating/cooling/idle)
- [ ] Show relay states visually
- [ ] Add manual override buttons

**Component**:
```tsx
<TemperatureControl
  mode="auto"
  setpoint={25}
  hysteresis={0.5}
  currentTemp={24.2}
  status="heating"
  onModeChange={...}
  onSetpointChange={...}
/>
```

**Files**:
- `frontend/src/components/TemperatureControl.tsx`
- `frontend/src/components/TemperatureControl.css`

---

### 7. Frontend: Alert Configuration

**Purpose**: UI for alert thresholds

**Tasks**:
- [ ] Add alert settings to temperature panel
- [ ] High/low temperature threshold inputs
- [ ] Alert enable/disable toggles
- [ ] Show active alerts

**Files**:
- `frontend/src/components/settings/TemperaturePanel.tsx` (extend)

---

### 8. Frontend: Control History

**Purpose**: View control events

**Tasks**:
- [ ] Add control event log to TemperaturePage
- [ ] Show heater/cooler on/off times
- [ ] Calculate runtime statistics
- [ ] Overlay control events on temperature chart

**Files**:
- `frontend/src/pages/TemperaturePage.tsx` (extend)
- `frontend/src/components/ControlEventLog.tsx` (new)

---

## Safety Requirements

### Hardware Safety
- [ ] Maximum heater runtime limit (prevent runaway heating)
- [ ] Minimum off-time between cycles (protect compressors)
- [ ] Failsafe: heater OFF on sensor failure
- [ ] Failsafe: cooler OFF on sensor failure
- [ ] Never run heater and cooler simultaneously

### Software Safety
- [ ] Persist control state to survive restarts
- [ ] Watchdog timer for controller service
- [ ] Alert on extended deviation from setpoint
- [ ] Manual override always available

---

## Testing Requirements

### Backend Tests
- [ ] Unit tests for relay service
- [ ] Unit tests for temperature controller (all modes)
- [ ] Test hysteresis behavior
- [ ] Test safety limits
- [ ] API endpoint tests

### Frontend Tests
- [ ] Component tests for TemperatureControl
- [ ] Test mode switching
- [ ] Test setpoint changes

### Hardware Tests (on Pi)
- [ ] Verify relay switching
- [ ] Test heater ON/OFF cycles
- [ ] Test cooler ON/OFF cycles (if available)
- [ ] Test auto mode switching
- [ ] Long-running control test (24h)

---

## Quality Gate

- [ ] All safety features implemented and tested
- [ ] No HIGH or CRITICAL issues
- [ ] Temperature maintained within setpoint ±1°C
- [ ] All alerts trigger correctly

---

## Success Criteria

1. Can maintain chamber at setpoint ±1°C
2. Alerts trigger when limits exceeded
3. Manual override always available
4. Control events logged and viewable
5. Survives restart and power cycle
6. Fails safe when sensor disconnected

---

## Notes

- Hysteresis prevents rapid cycling; start with 0.5°C
- PID control optional; simple on/off usually sufficient
- Consider relay lifespan; SSR better for frequent switching
- Document wiring and safety precautions for users

---

**Estimated Effort**: 3-4 days
**Dependencies**: Phase 1 complete
**Enables**: Temperature profiles in Phase 4
