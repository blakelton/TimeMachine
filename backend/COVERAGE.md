# Test Coverage Report

**Generated:** 2026-01-03 16:25:00
**Branch:** develop
**Commit:** b0b7579

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 164 |
| Passed | 164 |
| Failed |  |
| Warnings | 14 |
| **Coverage** | **40%** |

## Coverage by Module

| Module | Stmts | Miss | Cover | Status |
|--------|-------|------|-------|--------|
| `api/routes/cameras/capture.py` | 80 | 50 | 38% | 🔶 |
| `api/routes/cameras/crud.py` | 78 | 44 | 44% | 🔶 |
| `api/routes/cameras/dashboard.py` | 65 | 49 | 25% | 🔶 |
| `api/routes/cameras/discovery.py` | 30 | 18 | 40% | 🔶 |
| `api/routes/cameras/health.py` | 19 | 8 | 58% | ⚠️ |
| `api/routes/cameras/preview.py` | 101 | 80 | 21% | 🔶 |
| `api/routes/cameras/recording.py` | 46 | 30 | 35% | 🔶 |
| `api/routes/cameras/timelapse.py` | 97 | 62 | 36% | 🔶 |
| `api/routes/environment.py` | 156 | 124 | 21% | 🔶 |
| `api/routes/health.py` | 13 | 0 | 100% | ✅ |
| `api/routes/jobs.py` | 53 | 23 | 57% | ⚠️ |
| `api/routes/observations/batch.py` | 63 | 48 | 24% | 🔶 |
| `api/routes/observations/crud.py` | 72 | 36 | 50% | ⚠️ |
| `api/routes/observations/lifecycle.py` | 40 | 20 | 50% | ⚠️ |
| `api/routes/observations/media.py` | 58 | 38 | 34% | 🔶 |
| `api/routes/output_config.py` | 23 | 10 | 57% | ⚠️ |
| `api/routes/storage.py` | 69 | 47 | 32% | 🔶 |
| `api/routes/temperature.py` | 63 | 42 | 33% | 🔶 |
| `api/routes/websocket.py` | 15 | 8 | 47% | 🔶 |
| `core/config.py` | 47 | 4 | 91% | ✅ |
| `core/constants.py` | 30 | 0 | 100% | ✅ |
| `core/exceptions.py` | 57 | 22 | 61% | ⚠️ |
| `core/logging.py` | 31 | 4 | 87% | ✅ |
| `core/paths.py` | 39 | 18 | 54% | ⚠️ |
| `core/rate_limit.py` | 9 | 2 | 78% | ⚠️ |
| `core/resources.py` | 41 | 26 | 37% | 🔶 |
| `core/security.py` | 19 | 19 | 0% | ❌ |
| `db/base.py` | 3 | 0 | 100% | ✅ |
| `db/models/camera.py` | 21 | 0 | 100% | ✅ |
| `db/models/environment_device.py` | 33 | 0 | 100% | ✅ |
| `db/models/environment_reading.py` | 15 | 0 | 100% | ✅ |
| `db/models/event.py` | 13 | 0 | 100% | ✅ |
| `db/models/job.py` | 23 | 0 | 100% | ✅ |
| `db/models/observation.py` | 27 | 0 | 100% | ✅ |
| `db/models/output_config.py` | 17 | 0 | 100% | ✅ |
| `db/models/temperature_config.py` | 16 | 0 | 100% | ✅ |
| `db/repositories/base.py` | 42 | 7 | 83% | ✅ |
| `db/repositories/camera.py` | 25 | 10 | 60% | ⚠️ |
| `db/repositories/environment_device.py` | 18 | 8 | 56% | ⚠️ |
| `db/repositories/environment_reading.py` | 34 | 21 | 38% | 🔶 |
| `db/repositories/job.py` | 55 | 3 | 95% | ✅ |
| `db/repositories/observation.py` | 104 | 20 | 81% | ✅ |
| `db/repositories/output_config.py` | 15 | 7 | 53% | ⚠️ |
| `db/session.py` | 53 | 27 | 49% | 🔶 |
| `main.py` | 75 | 37 | 51% | ⚠️ |
| `models/schemas/base.py` | 49 | 0 | 100% | ✅ |
| `models/schemas/temperature.py` | 32 | 0 | 100% | ✅ |
| `models/schemas/websocket.py` | 32 | 0 | 100% | ✅ |
| `schemas/camera.py` | 72 | 0 | 100% | ✅ |
| `schemas/environment.py` | 107 | 0 | 100% | ✅ |
| `schemas/job.py` | 50 | 0 | 100% | ✅ |
| `schemas/observation.py` | 115 | 8 | 93% | ✅ |
| `schemas/output_config.py` | 25 | 0 | 100% | ✅ |
| `schemas/storage.py` | 34 | 0 | 100% | ✅ |
| `services/camera/capture.py` | 48 | 36 | 25% | 🔶 |
| `services/camera/device.py` | 25 | 20 | 20% | 🔶 |
| `services/camera/discovery.py` | 207 | 177 | 14% | 🔶 |
| `services/camera/health.py` | 126 | 126 | 0% | ❌ |
| `services/camera/overlay.py` | 182 | 151 | 17% | 🔶 |
| `services/camera/pipeline.py` | 161 | 126 | 22% | 🔶 |
| `services/camera/preview.py` | 163 | 136 | 17% | 🔶 |
| `services/camera/recording.py` | 158 | 127 | 20% | 🔶 |
| `services/camera/resolver.py` | 62 | 62 | 0% | ❌ |
| `services/camera/timelapse.py` | 2 | 2 | 0% | ❌ |
| `services/camera/timelapse/assembly.py` | 48 | 40 | 17% | 🔶 |
| `services/camera/timelapse/config.py` | 30 | 11 | 63% | ⚠️ |
| `services/camera/timelapse/service.py` | 225 | 185 | 18% | 🔶 |
| `services/camera/timelapse/session.py` | 234 | 151 | 35% | 🔶 |
| `services/camera/validation.py` | 42 | 4 | 90% | ✅ |
| `services/camera_device_monitor.py` | 47 | 47 | 0% | ❌ |
| `services/environment/polling.py` | 128 | 75 | 41% | 🔶 |
| `services/environment/sensors.py` | 187 | 134 | 28% | 🔶 |
| `services/observation/completion.py` | 14 | 0 | 100% | ✅ |
| `services/observation/lifecycle.py` | 149 | 128 | 14% | 🔶 |
| `services/observation/media.py` | 44 | 44 | 0% | ❌ |
| `services/observation/metadata.py` | 62 | 47 | 24% | 🔶 |
| `services/observation/preview.py` | 127 | 118 | 7% | 🔶 |
| `services/observation/progress.py` | 85 | 68 | 20% | 🔶 |
| `services/observation/service.py` | 199 | 150 | 25% | 🔶 |
| `services/observation/utils.py` | 31 | 25 | 19% | 🔶 |
| `services/startup.py` | 143 | 143 | 0% | ❌ |
| `services/stats_broadcaster.py` | 19 | 19 | 0% | ❌ |
| `services/storage/service.py` | 237 | 100 | 58% | ⚠️ |
| `services/system/stats.py` | 98 | 42 | 57% | ⚠️ |
| `services/system/throttle.py` | 49 | 16 | 67% | ⚠️ |
| `services/thumbnail/service.py` | 105 | 88 | 16% | 🔶 |
| `services/websocket/manager.py` | 58 | 6 | 90% | ✅ |

### Coverage Legend

| Status | Meaning |
|--------|---------|
| ✅ | 80%+ coverage (good) |
| ⚠️ | 50-79% coverage (acceptable) |
| 🔶 | 1-49% coverage (needs improvement) |
| ❌ | 0% coverage (not tested) |

## Test Files

| Test File | Tests |
|-----------|-------|
| `test_environment_services.py` | 9 |
| `test_polling_service.py` | 9 |
| `test_repositories.py` | 30 |
| `test_timelapse_regressions.py` | 18 |
| `test_validation_service.py` | 11 |
| `api/test_cameras.py` | 11 |
| `api/test_health.py` | 4 |
| `api/test_jobs.py` | 8 |
| `api/test_observations.py` | 9 |
| `api/test_timelapse.py` | 8 |
| `services/test_storage_service.py` | 19 |
| `services/test_timelapse_service.py` | 17 |
| `services/test_websocket_manager.py` | 11 |

## Notes

### Hardware-Dependent Code (Expected Low Coverage)

The following modules have low coverage because they require real hardware:

- `services/camera/*` - Requires physical cameras, GStreamer, v4l2
- `services/environment/*` - Requires GPIO, I2C sensors
- `services/observation/*` - Integration with camera subsystems

### Running Tests

```bash
# Quick test run
cd backend && pytest tests/ -v

# With coverage report
cd backend && pytest tests/ --cov=app --cov-report=html

# Run specific test file
cd backend && pytest tests/test_timelapse_regressions.py -v

# Run smoke tests after deployment
./scripts/smoke-test.sh
```

### Improving Coverage

To increase coverage for hardware-dependent code:

1. Create mock implementations for camera/sensor interfaces
2. Use dependency injection to swap real hardware for mocks
3. Add integration tests that run on actual hardware (CI excluded)
