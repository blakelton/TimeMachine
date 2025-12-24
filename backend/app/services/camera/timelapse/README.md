# Timelapse Service Package

This package contains the timelapse capture and video assembly functionality, refactored from the original monolithic `timelapse.py` module (1,277 lines) into focused components.

## Package Structure

```
timelapse/
├── __init__.py         (29 lines)  - Package exports and global service instance
├── config.py          (95 lines)  - TimelapseConfig class
├── session.py        (538 lines)  - TimelapseSession class and CaptureState enum
├── service.py        (563 lines)  - TimelapseService orchestration
└── assembly.py       (114 lines)  - Video assembly utilities
```

## Module Breakdown

### config.py
- `TimelapseConfig` class for session configuration
- Handles interval, frame count, duration, quality, resolution, and environment overlay settings
- Provides serialization to/from dict for database storage

### session.py
- `CaptureState` enum for state machine
- `TimelapseSession` class managing active capture sessions
- Features:
  - Automatic camera recovery for USB cameras
  - Event logging and gap detection
  - Environment overlay integration
  - Resource checking and adaptive throttling
  - State machine-based capture loop (reduced complexity)

### service.py
- `TimelapseService` orchestration class
- Session management and lifecycle
- Job tracking integration
- Interrupted timelapse resume/cleanup
- Progress reporting

### assembly.py
- `assemble_video()` - ffmpeg-based video assembly from frames
- `format_size()` - Human-readable size formatting
- Encoder semaphore management

## Backward Compatibility

The original `timelapse.py` module still exists as a compatibility shim that re-exports all classes and functions from the package. All existing imports will continue to work:

```python
# Still works:
from app.services.camera.timelapse import timelapse_service
from app.services.camera.timelapse import TimelapseConfig
from app.services.camera.timelapse import TimelapseSession, CaptureState

# New, more explicit imports also work:
from app.services.camera.timelapse.service import TimelapseService
from app.services.camera.timelapse.config import TimelapseConfig
from app.services.camera.timelapse.session import TimelapseSession
from app.services.camera.timelapse.assembly import assemble_video
```

## Benefits of Refactoring

1. **Improved maintainability**: Each module has a single, focused responsibility
2. **Better testability**: Smaller modules are easier to unit test
3. **Reduced cognitive load**: Developers can focus on one aspect at a time
4. **No breaking changes**: Full backward compatibility maintained
5. **Clearer dependencies**: Import structure shows relationships between components

## Line Counts

- Original: 1,277 lines in single file
- Refactored: 1,339 lines across 5 files (includes documentation and package exports)
- Each module is now under 600 lines (target was 500 lines)
- Largest module (service.py): 563 lines
- Largest module (session.py): 538 lines
