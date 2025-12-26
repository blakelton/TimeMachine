# Phase 1: Temperature Monitoring

> Implement DHT22 sensor reading and display

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: Phase 0 (Code Quality Remediation)

---

## Objective

Implement full DHT22 temperature and humidity monitoring with real-time display, historical data, and WebSocket updates. This establishes the foundation for Phase 2 (Temperature Control).

## Prerequisites

- [ ] Phase 0 complete (code quality issues resolved)
- [ ] DHT22 sensor available for testing
- [ ] GPIO access configured on Raspberry Pi

## Hardware

**Sensor**: DHT22 / AM2302
- Temperature range: -40°C to 80°C (±0.5°C accuracy)
- Humidity range: 0-100% RH (±2-5% accuracy)
- Sampling rate: 0.5Hz (one reading per 2 seconds)

**Wiring** (default configuration):
- VCC → 3.3V or 5V
- DATA → GPIO4 (configurable)
- GND → Ground

---

## Deliverables

### 1. Backend: DHT22 Driver Service

**Purpose**: Read temperature/humidity from DHT22 sensor

**Tasks**:
- [ ] Create `backend/app/services/temperature/dht22.py`
- [ ] Implement Adafruit_DHT or adafruit-circuitpython-dht integration
- [ ] Add retry logic for failed readings (DHT22 is timing-sensitive)
- [ ] Handle sensor not connected gracefully
- [ ] Implement async reading to avoid blocking
- [ ] Add GPIO pin configuration
- [ ] Create mock mode for development without hardware

**Interface**:
```python
class DHT22Service:
    async def read() -> TempReading | None
    async def get_status() -> SensorStatus
    def configure(gpio_pin: int) -> None
```

**Files**:
- `backend/app/services/temperature/dht22.py` (new)
- `backend/app/services/temperature/__init__.py` (new)

---

### 2. Backend: Database Model

**Purpose**: Store temperature readings and configuration

**Tasks**:
- [ ] Create TemperatureReading model (extends existing stub if present)
- [ ] Create TemperatureConfig model (GPIO pin, units, etc.)
- [ ] Add SQLAlchemy migrations
- [ ] Create repository with efficient queries for time ranges
- [ ] Add data retention for readings (configurable)

**Schema**:
```python
class TemperatureReading:
    id: int
    timestamp: datetime
    temperature_c: float
    humidity: float | None
    sensor_id: str

class TemperatureConfig:
    id: int
    gpio_pin: int
    polling_interval_seconds: int
    units: str  # "celsius" | "fahrenheit"
    enabled: bool
```

**Files**:
- `backend/app/db/models/temperature.py`
- `backend/app/db/repositories/temperature.py`

---

### 3. Backend: API Endpoints

**Purpose**: Expose temperature data via REST API

**Endpoints**:
```
GET  /api/v1/temperature/current    → Current reading
GET  /api/v1/temperature/history    → Historical readings (with time range)
GET  /api/v1/temperature/config     → Get configuration
PUT  /api/v1/temperature/config     → Update configuration
GET  /api/v1/temperature/status     → Sensor status
```

**Tasks**:
- [ ] Create temperature router
- [ ] Implement current reading endpoint
- [ ] Implement history endpoint with pagination and time filters
- [ ] Implement config endpoints
- [ ] Add validation and error handling
- [ ] Update OpenAPI schema

**Files**:
- `backend/app/api/routes/temperature.py` (new or extend stub)
- `backend/app/schemas/temperature.py`

---

### 4. Backend: WebSocket Integration

**Purpose**: Real-time temperature updates to connected clients

**Tasks**:
- [ ] Add temperature reading to stats broadcast
- [ ] Create dedicated temperature update message type
- [ ] Configure broadcast interval (match sensor polling)
- [ ] Handle sensor errors gracefully in broadcast

**Message Format**:
```json
{
  "type": "temperature_update",
  "data": {
    "temperature_c": 23.5,
    "temperature_f": 74.3,
    "humidity": 45.2,
    "timestamp": "2025-12-21T10:30:00Z",
    "status": "ok"
  }
}
```

**Files**:
- `backend/app/services/websocket_manager.py`
- `backend/app/services/stats_broadcaster.py`

---

### 5. Backend: Background Service

**Purpose**: Continuous sensor polling and data storage

**Tasks**:
- [ ] Create temperature polling service
- [ ] Integrate with FastAPI lifespan
- [ ] Implement configurable polling interval
- [ ] Add health checks for sensor connectivity
- [ ] Handle startup when sensor not connected
- [ ] Add graceful shutdown

**Files**:
- `backend/app/services/temperature/polling.py`
- `backend/app/main.py` (update lifespan)

---

### 6. Frontend: Temperature Display Component

**Purpose**: Show current temperature/humidity

**Tasks**:
- [ ] Create `TemperatureDisplay.tsx` component
- [ ] Show temperature with unit toggle (°C/°F)
- [ ] Show humidity percentage
- [ ] Add trend indicator (rising/falling/stable)
- [ ] Handle loading and error states
- [ ] Integrate with WebSocket for real-time updates

**Component**:
```tsx
<TemperatureDisplay
  temperature={23.5}
  humidity={45.2}
  unit="celsius"
  trend="stable"
  lastUpdated={timestamp}
/>
```

**Files**:
- `frontend/src/components/TemperatureDisplay.tsx`
- `frontend/src/components/TemperatureDisplay.css`

---

### 7. Frontend: Temperature History Chart

**Purpose**: Visualize temperature over time

**Tasks**:
- [ ] Create `TemperatureChart.tsx` component
- [ ] Use a charting library (recharts, Chart.js, or similar)
- [ ] Show temperature and humidity as separate lines
- [ ] Add time range selector (1h, 6h, 24h, 7d)
- [ ] Support zoom and pan
- [ ] Responsive design for mobile

**Files**:
- `frontend/src/components/TemperatureChart.tsx`
- `frontend/src/components/TemperatureChart.css`

---

### 8. Frontend: Dashboard Integration

**Purpose**: Add temperature to Home dashboard

**Tasks**:
- [ ] Add TemperatureDisplay to HomePage
- [ ] Position in system stats area
- [ ] Ensure proper layout with existing components
- [ ] Add click-through to detailed view

**Files**:
- `frontend/src/pages/HomePage.tsx`

---

### 9. Frontend: Temperature Page

**Purpose**: Dedicated page for temperature details

**Tasks**:
- [ ] Create TemperaturePage with chart and stats
- [ ] Add to React Router
- [ ] Add to navigation
- [ ] Show min/max/average for selected period
- [ ] Optional: Add export to CSV

**Files**:
- `frontend/src/pages/TemperaturePage.tsx`
- `frontend/src/pages/TemperaturePage.css`
- `frontend/src/App.tsx` (routes)
- `frontend/src/components/Layout.tsx` (navigation)

---

### 10. Frontend: Settings Panel

**Purpose**: Configure temperature sensor

**Tasks**:
- [ ] Update existing Temperature stub panel in Settings
- [ ] Add GPIO pin configuration
- [ ] Add polling interval setting
- [ ] Add unit preference (°C/°F)
- [ ] Add enable/disable toggle
- [ ] Show sensor status/health

**Files**:
- `frontend/src/components/settings/TemperaturePanel.tsx`
- `frontend/src/pages/SystemPage.tsx`

---

## Testing Requirements

### Backend Tests
- [ ] Unit tests for DHT22 service (with mocking)
- [ ] Unit tests for temperature repository
- [ ] API endpoint tests
- [ ] WebSocket message tests

### Frontend Tests
- [ ] Component tests for TemperatureDisplay
- [ ] Component tests for TemperatureChart
- [ ] Integration test for temperature page

### Hardware Tests (on Pi)
- [ ] Verify sensor readings match reference thermometer
- [ ] Test with sensor disconnected
- [ ] Test reconnection after disconnect
- [ ] Long-running stability test (24h)

---

## Quality Gate

- [ ] All new code passes linting (ruff, eslint)
- [ ] Type checking passes (mypy, TypeScript)
- [ ] Test coverage > 80% for new code
- [ ] No new HIGH or CRITICAL issues
- [ ] Sensor readings within ±0.5°C of reference

---

## Success Criteria

1. Live temperature/humidity displayed on Home dashboard
2. Historical data viewable in charts
3. Readings persist to database
4. WebSocket updates work in real-time
5. Configuration persists across restarts
6. Graceful handling when sensor unavailable

---

## Notes

- DHT22 is timing-sensitive; may need dedicated thread
- Consider rate limiting database writes (aggregate readings)
- Mock mode essential for development on non-Pi systems
- Humidity calibration may drift over time

---

**Estimated Effort**: 2-3 days
**Dependencies**: Phase 0 complete
**Enables**: Phase 2 (Temperature Control)
