# Feature: Camera Services Implementation

## Overview

Complete the TimeMachine camera services implementation including GStreamer pipeline management with crash recovery, H.264 encoder semaphore management, pre-flight resource checks, and the missing timelapse service. This plan addresses critical gaps in the existing camera service architecture that prevent core camera operations from working.

## Requirements

### Functional Requirements
- FR1: GStreamer pipelines must support start, stop, crash recovery, and graceful shutdown
- FR2: H.264 encoder must be protected by semaphore (single encoder on Pi 3)
- FR3: Pre-flight checks must validate memory (>=100MB) and disk space (>=500MB) before operations
- FR4: Preview service must stream MJPEG from both CSI and USB cameras
- FR5: Capture service must save still images with configurable quality
- FR6: Recording service must create H.264-encoded MP4 files with proper file finalization
- FR7: Timelapse service must capture frames at intervals, persist progress, resume after interruption, and assemble to video
- FR8: All services must track active operations with PIDs for state management
- FR9: Orphan process cleanup on startup to recover from crashes

### Non-Functional Requirements
- NFR1: Memory usage must stay within 700MB total for all services combined
- NFR2: Pipeline startup latency < 2 seconds
- NFR3: Preview latency < 500ms
- NFR4: All operations must be non-blocking (async)
- NFR5: Logging must include structured data for debugging
- NFR6: Graceful degradation when resources unavailable

### Success Criteria
- Preview works for both CSI and USB cameras with crash recovery
- Recording creates valid MP4 files using hardware H.264 encoder
- Only one recording can use the encoder at a time (semaphore enforced)
- Timelapse captures frames, tracks progress in database, and assembles to video
- System blocks operations when memory < 100MB or disk < 500MB
- Orphan processes from previous crashes are cleaned up on startup

## Architectural Analysis

### Existing Components Affected

- **`app/services/camera/pipeline.py`**: ManagedPipeline class exists with basic state management and crash recovery. Needs: state persistence, better error classification, EOS (End of Stream) handling for recordings.

- **`app/services/camera/preview.py`**: PreviewService exists with CSI/USB pipeline builders. Needs: integration with proper stream cleanup, port management improvements.

- **`app/services/camera/capture.py`**: CaptureService exists with basic capture commands. Needs: quality settings integration, better error handling.

- **`app/services/camera/recording.py`**: RecordingService exists with encoder semaphore integration. Needs: file finalization handling (mp4mux requires EOS signal), PID persistence to database.

- **`app/services/camera/discovery.py`**: Complete - no changes needed.

- **`app/core/resources.py`**: EncoderSemaphore and check_resources_available exist. Needs: fix signature mismatch with stats.py functions.

- **`app/services/system/stats.py`**: check_memory_available and check_disk_available return bool only. Needs: return tuple `(bool, int)` to match resources.py expectations.

- **`app/db/models/job.py`**: Job model exists with timelapse fields. Complete for timelapse support.

- **`app/api/routes/cameras.py`**: API routes exist for preview, capture, recording. Needs: timelapse endpoints.

- **`app/services/camera/__init__.py`**: Only exports CameraDiscovery. Needs: export all services.

### New Components Required

- **`app/services/camera/timelapse.py`**: New service for timelapse capture and assembly
  - Frame capture at configurable intervals
  - Progress tracking with Job model
  - Resume capability after interruption
  - Video assembly using ffmpeg
  - Cleanup of temporary frames

- **`app/services/camera/startup.py`**: New module for startup initialization
  - Orphan process cleanup (kill stale gst-launch processes)
  - Recovery from interrupted jobs in database
  - State reconciliation

### Data Model Changes

- **No schema changes needed**: Job model already has timelapse fields (timelapse_config, timelapse_progress, timelapse_dir)

### State/Workflow Design

**Pipeline States** (existing in PipelineState enum):
- `IDLE`: Not started
- `STARTING`: Launch in progress
- `RUNNING`: Active and healthy
- `STOPPING`: Shutdown in progress
- `STOPPED`: Clean termination
- `ERROR`: Unrecoverable error
- `CRASHED`: Unexpected termination (triggers recovery)

**Recording Workflow**:
1. Check encoder semaphore availability
2. Acquire semaphore (blocking wait with timeout)
3. Pre-flight checks (memory, disk)
4. Start GStreamer pipeline
5. Track PID in database Job record
6. On stop: send EOS signal, wait for file finalization
7. Release semaphore
8. Update Job status

**Timelapse Workflow**:
1. Create Job record with status "pending"
2. Create timelapse directory
3. Capture loop:
   - Check if job interrupted
   - Capture frame (uses CaptureService)
   - Update Job.timelapse_progress
   - Sleep for interval
4. On completion: assemble frames to video using ffmpeg
5. Update Job status to "completed"
6. Optionally cleanup frames

## Implementation Plan

### Phase 1: Fix Foundation Issues

**Goal**: Fix signature mismatches and ensure base services work correctly.

**Tasks**:

1. **Task 1.1**: Fix stats.py function signatures
   - **Architecture**: Modify `check_memory_available` and `check_disk_available` to return `tuple[bool, int]` containing success status and available MB
   - **Considerations**: Maintains backward compatibility by allowing unpacking or direct bool check
   - **Dependencies**: None
   - **Testing**: Unit test that functions return correct tuple format
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/system/stats.py`

2. **Task 1.2**: Update camera services __init__.py exports
   - **Architecture**: Export preview_service, capture_service, recording_service instances
   - **Considerations**: Avoid circular imports by using lazy imports where necessary
   - **Dependencies**: None
   - **Testing**: Import test to verify all exports work
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/__init__.py`

3. **Task 1.3**: Enhance ManagedPipeline with EOS support
   - **Architecture**: Add `send_eos()` method that sends SIGINT to gst-launch for clean mp4mux finalization
   - **Considerations**: mp4mux requires EOS to write moov atom; SIGTERM doesn't allow this
   - **Dependencies**: Task 1.1
   - **Testing**: Test that stop() sends EOS before terminate, verify MP4 is playable
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/pipeline.py`

**Deliverables**:
- Fixed function signatures in stats.py
- Complete exports in camera __init__.py
- EOS support in ManagedPipeline

**Acceptance Criteria**:
- `check_resources_available()` works without exceptions
- All camera services importable from `app.services.camera`
- Recordings produce playable MP4 files

---

### Phase 2: Enhanced Recording Service

**Goal**: Make recording service robust with proper file finalization and database tracking.

**Tasks**:

1. **Task 2.1**: Add Job database integration to RecordingService
   - **Architecture**: Create Job record on start, update status on stop/error
   - **Considerations**: Must handle database session lifecycle correctly in async context
   - **Dependencies**: Phase 1 complete
   - **Testing**: Verify Job records created/updated for recordings
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/recording.py`

2. **Task 2.2**: Implement graceful recording stop with EOS
   - **Architecture**: On stop_recording(), call pipeline.send_eos(), wait up to 5s for clean shutdown, then terminate if needed
   - **Considerations**: User may want to cancel recording immediately; provide force flag
   - **Dependencies**: Task 1.3
   - **Testing**: Verify MP4 files have valid moov atom after stop
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/recording.py`

3. **Task 2.3**: Add disk space estimation for recordings
   - **Architecture**: Estimate required disk space: `(bitrate_bps / 8) * duration_seconds * 1.1` (10% overhead)
   - **Considerations**: Check against available space before starting
   - **Dependencies**: Task 1.1
   - **Testing**: Verify pre-flight check fails when insufficient space
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/recording.py`

4. **Task 2.4**: Enhance encoder semaphore with timeout and queue info
   - **Architecture**: Add `try_acquire(timeout_seconds)` method, add `queue_position()` method
   - **Considerations**: Current acquire() blocks forever; need timeout for better UX
   - **Dependencies**: None
   - **Testing**: Verify timeout works, verify queue position reported
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/core/resources.py`

**Deliverables**:
- Recording service with database integration
- Clean MP4 file finalization
- Disk space estimation
- Enhanced encoder semaphore

**Acceptance Criteria**:
- Recordings tracked in Job table
- MP4 files playable after stop
- Recordings blocked when disk space insufficient
- Encoder semaphore timeout works

---

### Phase 3: Timelapse Service Implementation

**Goal**: Create complete timelapse service with capture, progress tracking, and video assembly.

**Tasks**:

1. **Task 3.1**: Create TimelapseService class structure
   - **Architecture**:
     ```python
     class TimelapseService:
         async def start_timelapse(camera_id, interval_seconds, total_frames, quality) -> Job
         async def stop_timelapse(job_id) -> bool
         async def get_timelapse_status(job_id) -> TimelapseStatus
         async def resume_timelapse(job_id) -> bool
         async def assemble_timelapse(job_id, fps, output_path) -> str
     ```
   - **Considerations**: Must be interruptible, progress must persist
   - **Dependencies**: Phase 2 complete
   - **Testing**: Unit test class instantiation and method signatures
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

2. **Task 3.2**: Implement frame capture loop
   - **Architecture**:
     - Create background task for capture loop
     - Use CaptureService for individual frames
     - Store frames as `frame_00001.jpg`, `frame_00002.jpg`, etc.
     - Update Job.timelapse_progress after each frame
   - **Considerations**: Must handle camera errors gracefully, continue on transient failures
   - **Dependencies**: Task 3.1
   - **Testing**: Verify frames captured at correct intervals, progress updated
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

3. **Task 3.3**: Implement timelapse resume capability
   - **Architecture**:
     - On startup, query Jobs with status "running" and job_type "timelapse"
     - Read existing frames from timelapse_dir
     - Set timelapse_progress to frame count
     - Resume capture loop from current progress
   - **Considerations**: Frame numbering must be consistent after resume
   - **Dependencies**: Task 3.2
   - **Testing**: Stop service mid-timelapse, restart, verify resume works
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

4. **Task 3.4**: Implement video assembly with ffmpeg
   - **Architecture**:
     - Use subprocess to call ffmpeg
     - Command: `ffmpeg -framerate {fps} -i {dir}/frame_%05d.jpg -c:v libx264 -pix_fmt yuv420p {output}`
     - Run in thread executor to avoid blocking
   - **Considerations**: ffmpeg must be installed; add to deployment requirements
   - **Dependencies**: Task 3.2
   - **Testing**: Verify assembled video is playable
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

5. **Task 3.5**: Add frame cleanup option
   - **Architecture**: Optional cleanup of frame directory after successful assembly
   - **Considerations**: User may want to keep frames for re-assembly at different fps
   - **Dependencies**: Task 3.4
   - **Testing**: Verify frames deleted when cleanup=True
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

**Deliverables**:
- Complete TimelapseService class
- Frame capture with progress tracking
- Resume capability
- Video assembly
- Frame cleanup

**Acceptance Criteria**:
- Timelapse captures frames at configured intervals
- Progress persists in database
- Timelapse resumes after interruption
- Assembled video is playable
- Frames can be cleaned up

---

### Phase 4: API Endpoints and Integration

**Goal**: Expose timelapse functionality through API and integrate all services.

**Tasks**:

1. **Task 4.1**: Add timelapse Pydantic schemas
   - **Architecture**:
     ```python
     class TimelapseCreate(BaseModel):
         camera_id: int
         interval_seconds: float
         total_frames: int
         quality: int = 85

     class TimelapseStatus(BaseModel):
         job_id: int
         status: str
         current_frame: int
         total_frames: int
         elapsed_seconds: float
         estimated_remaining_seconds: float
     ```
   - **Considerations**: Follow existing schema patterns
   - **Dependencies**: Phase 3 complete
   - **Testing**: Schema validation tests
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/schemas/camera.py`

2. **Task 4.2**: Add timelapse API endpoints
   - **Architecture**:
     ```python
     @router.post("/{camera_id}/timelapse/start")
     @router.post("/{camera_id}/timelapse/stop")
     @router.get("/{camera_id}/timelapse/{job_id}/status")
     @router.post("/{camera_id}/timelapse/{job_id}/assemble")
     ```
   - **Considerations**: Follow existing endpoint patterns in cameras.py
   - **Dependencies**: Task 4.1
   - **Testing**: Integration tests for each endpoint
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/api/routes/cameras.py`

3. **Task 4.3**: Create startup cleanup module
   - **Architecture**:
     - Find orphan gst-launch-1.0 processes from previous runs
     - Kill orphan processes
     - Update Job records with status "interrupted" for incomplete jobs
   - **Considerations**: Must not kill other users' gst-launch processes; use PID tracking
   - **Dependencies**: Task 2.1
   - **Testing**: Simulate crash, verify cleanup on restart
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/startup.py`

4. **Task 4.4**: Integrate startup cleanup into main.py lifespan
   - **Architecture**: Call startup cleanup in lifespan startup phase
   - **Considerations**: Must complete before accepting requests
   - **Dependencies**: Task 4.3
   - **Testing**: Integration test with crash simulation
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/main.py`

5. **Task 4.5**: Export timelapse_service from __init__.py
   - **Architecture**: Add timelapse_service to exports
   - **Considerations**: Maintain consistency with other service exports
   - **Dependencies**: Task 3.1
   - **Testing**: Import test
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/__init__.py`

**Deliverables**:
- Timelapse schemas
- Timelapse API endpoints
- Startup cleanup module
- Full service integration

**Acceptance Criteria**:
- API endpoints work as documented
- Orphan processes cleaned on startup
- Interrupted jobs marked in database
- All services exportable and usable

---

### Phase 5: Testing and Hardening

**Goal**: Comprehensive testing and edge case handling.

**Tasks**:

1. **Task 5.1**: Create unit tests for TimelapseService
   - **Architecture**: Mock CaptureService and Job repository
   - **Considerations**: Test error conditions, boundary cases
   - **Dependencies**: Phase 3, Phase 4 complete
   - **Testing**: pytest with asyncio support
   - **File**: `/home/azuelab/projects/TimeMachine/backend/tests/services/camera/test_timelapse.py`

2. **Task 5.2**: Create integration tests for recording workflow
   - **Architecture**: Test full recording flow with database
   - **Considerations**: May need mock GStreamer for CI
   - **Dependencies**: Phase 2 complete
   - **Testing**: pytest-asyncio
   - **File**: `/home/azuelab/projects/TimeMachine/backend/tests/services/camera/test_recording.py`

3. **Task 5.3**: Add error recovery for pipeline crashes during recording
   - **Architecture**: On crash, attempt to salvage partial file using ffmpeg -copy
   - **Considerations**: Partial file may not be recoverable; log clearly
   - **Dependencies**: Phase 2 complete
   - **Testing**: Simulate crash, verify partial recovery attempted
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/recording.py`

4. **Task 5.4**: Add memory monitoring during long operations
   - **Architecture**: Periodic check during timelapse/recording, warn if memory drops below threshold
   - **Considerations**: Don't abort, just warn; let user decide
   - **Dependencies**: Phase 3 complete
   - **Testing**: Monitor logs during long timelapse
   - **File**: `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py`

**Deliverables**:
- Unit tests for timelapse
- Integration tests for recording
- Error recovery logic
- Memory monitoring

**Acceptance Criteria**:
- Test coverage > 70% for new code
- Crash recovery attempted
- Memory warnings logged when appropriate

## Design Principles Application

### SOLID Compliance

- **Single Responsibility**:
  - TimelapseService: only timelapse logic
  - CaptureService: only still capture
  - RecordingService: only video recording
  - EncoderSemaphore: only encoder access control

- **Open/Closed**:
  - ManagedPipeline accepts PipelineConfig for extension
  - New camera types can be added without modifying existing services

- **Liskov Substitution**:
  - All services follow async method patterns consistently

- **Interface Segregation**:
  - Services expose only methods relevant to their domain
  - API endpoints expose only what frontend needs

- **Dependency Inversion**:
  - Services depend on abstractions (PipelineConfig, Job model)
  - Database access through repository pattern

### DRY Analysis

- **Reusable Patterns**:
  - Resource checking: `check_resources_available()` used by all services
  - Pipeline management: `ManagedPipeline` used by preview and recording
  - File naming: extract to utility function

- **Common Utilities**:
  - `app/services/camera/utils.py`: file naming, directory creation
  - `app/core/resources.py`: resource checking, semaphore

### Complexity Management

- **Cyclomatic Complexity Strategy**:
  - Keep each method under CC 10
  - Extract condition branches into helper methods
  - Use early returns to reduce nesting

- **Cognitive Complexity Strategy**:
  - Max 3 nesting levels
  - Clear variable names
  - Comprehensive docstrings

- **Function Size Guidelines**:
  - Target 30-50 lines per method
  - Extract loops into generators
  - Split complex logic into private methods

### System Constraints

- **Resource Budget**:
  - Preview: ~80MB RAM
  - Recording: ~100MB RAM
  - Timelapse: ~50MB RAM (uses capture, not continuous)
  - Total: Stay under 700MB systemd limit

- **Performance Requirements**:
  - Pipeline startup: < 2 seconds
  - Preview latency: < 500ms
  - Frame capture: < 1 second

- **Security Considerations**:
  - Sanitize file paths (no directory traversal)
  - Validate camera_id against database
  - Rate limit API endpoints

- **Scalability Strategy**:
  - Single Pi deployment, not distributed
  - Semaphore enforces single encoder use
  - Background tasks for non-blocking operations

## Integration Points

- **CaptureService <-> TimelapseService**: TimelapseService uses CaptureService.capture_image() for frame capture
- **RecordingService <-> EncoderSemaphore**: Recording must acquire/release semaphore
- **All Services <-> check_resources_available**: Pre-flight checks before operations
- **All Services <-> Job Model**: Track operations in database
- **ManagedPipeline <-> All Pipeline Services**: Common pipeline abstraction

## Testing Strategy

- **Unit Tests**:
  - Mock subprocess for GStreamer commands
  - Mock database session for repository tests
  - Test error conditions and boundary cases

- **Integration Tests**:
  - Use test database
  - Test full API request cycle
  - Test service interactions

- **System Tests**:
  - On real Pi with cameras (manual)
  - End-to-end recording and timelapse

- **Performance Tests**:
  - Memory usage monitoring
  - Startup time measurement

## Risks and Mitigations

- **Risk 1**: GStreamer pipeline commands may vary between camera models
  - **Mitigation**: Make pipeline strings configurable; log actual commands for debugging

- **Risk 2**: MP4 file corruption on unclean shutdown
  - **Mitigation**: EOS signal handling; partial file recovery with ffmpeg

- **Risk 3**: Timelapse interrupted at frame 999 of 1000
  - **Mitigation**: Resume capability; progress persistence every frame

- **Risk 4**: Memory exhaustion during long timelapse
  - **Mitigation**: Periodic memory checks; frame-by-frame capture (no accumulation)

- **Risk 5**: ffmpeg not installed on target system
  - **Mitigation**: Add to deployment checklist; check on startup

## Dependencies and Prerequisites

- Python packages: Already in requirements.txt (psutil, structlog, pydantic)
- System packages:
  - `gstreamer1.0-plugins-good` - GStreamer plugins
  - `ffmpeg` - Video assembly
  - `v4l-utils` - Camera utilities
- Build system: No changes needed
- Database: No migrations needed (Job model already has timelapse fields)

## Timeline Estimate

- **Phase 1 (Foundation Fixes)**: 2-3 hours
- **Phase 2 (Recording Enhancement)**: 4-6 hours
- **Phase 3 (Timelapse Service)**: 8-10 hours
- **Phase 4 (API & Integration)**: 4-6 hours
- **Phase 5 (Testing & Hardening)**: 6-8 hours
- **Total**: 24-33 hours (3-4 days)

## File Summary

### Files to Modify
| File | Changes |
|------|---------|
| `/home/azuelab/projects/TimeMachine/backend/app/services/system/stats.py` | Fix return types |
| `/home/azuelab/projects/TimeMachine/backend/app/services/camera/__init__.py` | Add exports |
| `/home/azuelab/projects/TimeMachine/backend/app/services/camera/pipeline.py` | Add EOS support |
| `/home/azuelab/projects/TimeMachine/backend/app/services/camera/recording.py` | Add Job integration, EOS stop |
| `/home/azuelab/projects/TimeMachine/backend/app/core/resources.py` | Add semaphore timeout |
| `/home/azuelab/projects/TimeMachine/backend/app/api/routes/cameras.py` | Add timelapse endpoints |
| `/home/azuelab/projects/TimeMachine/backend/app/schemas/camera.py` | Add timelapse schemas |
| `/home/azuelab/projects/TimeMachine/backend/app/main.py` | Add startup cleanup |

### Files to Create
| File | Purpose |
|------|---------|
| `/home/azuelab/projects/TimeMachine/backend/app/services/camera/timelapse.py` | Timelapse service |
| `/home/azuelab/projects/TimeMachine/backend/app/services/camera/startup.py` | Startup cleanup |
| `/home/azuelab/projects/TimeMachine/backend/tests/services/camera/test_timelapse.py` | Unit tests |
| `/home/azuelab/projects/TimeMachine/backend/tests/services/camera/test_recording.py` | Integration tests |
