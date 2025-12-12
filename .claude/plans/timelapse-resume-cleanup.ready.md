# Feature: Timelapse Resume and Cleanup

## Overview
Implement functionality to detect, resume, or cleanup interrupted timelapses. When a timelapse is interrupted (power outage, service restart, user navigation), users should be able to either resume capturing or generate a video from the frames captured so far.

## Current State

**Backend**:
- Timelapse start/stop endpoints exist
- Jobs track timelapse status with `interrupted` state
- Frames are stored in `timelapse/{job_id}/` directory
- No resume or finalize endpoints

**Frontend**:
- TimelapseTab has start/stop only
- No detection of interrupted timelapses
- No resume UI
- No cleanup/finalize UI

## Requirements

### Functional Requirements
- FR1: Detect interrupted timelapses on camera page load
- FR2: Show resume banner when interrupted timelapse exists
- FR3: Resume interrupted timelapse (continue capturing)
- FR4: Finalize interrupted timelapse (generate video from existing frames)
- FR5: Cleanup interrupted timelapse (delete frames without generating video)
- FR6: Show frame count and disk usage for interrupted timelapse

### Non-Functional Requirements
- NFR1: Resume detection should be fast (<500ms)
- NFR2: Video generation should run as background job
- NFR3: Clear user feedback during all operations
- NFR4: Prevent data loss (confirm before cleanup)

## Backend Implementation

### New Endpoints

```
GET  /api/v1/cameras/{camera_id}/timelapse/interrupted
POST /api/v1/cameras/{camera_id}/timelapse/resume
POST /api/v1/cameras/{camera_id}/timelapse/finalize
DELETE /api/v1/cameras/{camera_id}/timelapse/cleanup
```

### API Design

#### GET /api/v1/cameras/{camera_id}/timelapse/interrupted

Check if there's an interrupted timelapse for this camera.

**Response** (200):
```json
{
  "has_interrupted": true,
  "job_id": 42,
  "frame_count": 150,
  "frames_directory": "/var/lib/timemachine/media/timelapse/job_42/",
  "disk_usage_bytes": 75000000,
  "disk_usage_human": "75.0 MB",
  "started_at": "2024-01-15T10:00:00Z",
  "interrupted_at": "2024-01-15T12:30:00Z",
  "original_config": {
    "interval_seconds": 60,
    "total_frames": 360,
    "quality": 90
  }
}
```

If no interrupted timelapse:
```json
{
  "has_interrupted": false
}
```

#### POST /api/v1/cameras/{camera_id}/timelapse/resume

Resume an interrupted timelapse.

**Response** (200):
```json
{
  "success": true,
  "message": "Timelapse resumed",
  "job_id": 42,
  "frames_captured": 150,
  "frames_remaining": 210
}
```

**Errors**:
- 404: No interrupted timelapse found
- 409: Another timelapse already running

#### POST /api/v1/cameras/{camera_id}/timelapse/finalize

Generate video from captured frames without continuing the timelapse.

**Request Body** (optional):
```json
{
  "output_fps": 30,
  "output_format": "mp4"
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "message": "Video generation started",
  "job_id": 43,
  "frame_count": 150,
  "estimated_duration_seconds": 5
}
```

**Errors**:
- 404: No interrupted timelapse found
- 400: No frames to process

#### DELETE /api/v1/cameras/{camera_id}/timelapse/cleanup

Delete frames from interrupted timelapse without generating video.

**Response** (200):
```json
{
  "success": true,
  "message": "Timelapse frames deleted",
  "frames_deleted": 150,
  "space_freed_bytes": 75000000,
  "space_freed_human": "75.0 MB"
}
```

**Errors**:
- 404: No interrupted timelapse found

### Backend Implementation

**Task 1: Add endpoints to cameras router**

File: `backend/app/api/routes/cameras.py`

```python
@router.get("/{camera_id}/timelapse/interrupted")
async def check_interrupted_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Check for interrupted timelapse on this camera."""
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        return {"has_interrupted": False}

    # Get frame info from filesystem
    frame_info = await timelapse_service.get_interrupted_frame_info(interrupted_job.id)

    return {
        "has_interrupted": True,
        "job_id": interrupted_job.id,
        "frame_count": frame_info["frame_count"],
        "frames_directory": frame_info["directory"],
        "disk_usage_bytes": frame_info["disk_usage_bytes"],
        "disk_usage_human": frame_info["disk_usage_human"],
        "started_at": interrupted_job.started_at,
        "interrupted_at": interrupted_job.updated_at,
        "original_config": interrupted_job.config,
    }


@router.post("/{camera_id}/timelapse/resume")
async def resume_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Resume an interrupted timelapse."""
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    success, message, job_id = await timelapse_service.resume_timelapse(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        session=session,
    )

    if not success:
        status_code = 404 if "not found" in message.lower() else 409
        raise HTTPException(status_code=status_code, detail=message)

    return {
        "success": True,
        "message": message,
        "job_id": job_id,
    }


@router.post("/{camera_id}/timelapse/finalize")
async def finalize_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    output_fps: int = 30,
):
    """Generate video from interrupted timelapse frames."""
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    success, message, job_id = await timelapse_service.finalize_interrupted(
        camera_id=camera_id,
        session=session,
        output_fps=output_fps,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "job_id": job_id,
    }


@router.delete("/{camera_id}/timelapse/cleanup")
async def cleanup_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete frames from interrupted timelapse."""
    success, message, stats = await timelapse_service.cleanup_interrupted(
        camera_id=camera_id,
        session=session,
    )

    if not success:
        raise HTTPException(status_code=404, detail=message)

    return {
        "success": True,
        "message": message,
        **stats,
    }
```

**Task 2: Add timelapse service methods**

File: `backend/app/services/camera/timelapse.py` - Add methods:

```python
async def get_interrupted_frame_info(self, job_id: int) -> dict:
    """Get information about frames from an interrupted timelapse."""
    frames_dir = Path(settings.TIMELAPSE_PATH) / f"job_{job_id}"

    if not frames_dir.exists():
        return {
            "frame_count": 0,
            "directory": str(frames_dir),
            "disk_usage_bytes": 0,
            "disk_usage_human": "0 B",
        }

    frames = list(frames_dir.glob("*.jpg"))
    total_size = sum(f.stat().st_size for f in frames)

    return {
        "frame_count": len(frames),
        "directory": str(frames_dir),
        "disk_usage_bytes": total_size,
        "disk_usage_human": self._format_size(total_size),
    }


async def resume_timelapse(
    self,
    camera_id: int,
    device_path: str,
    camera_type: str,
    session: AsyncSession,
) -> tuple[bool, str, int | None]:
    """Resume an interrupted timelapse."""
    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        return False, "No interrupted timelapse found", None

    # Check if another timelapse is running
    if self.is_running(camera_id):
        return False, "Another timelapse is already running", None

    # Update job status back to running
    await job_repo.update(interrupted_job.id, status="running")

    # Resume capture with remaining frames
    config = TimelapseConfig(**interrupted_job.config)
    frames_captured = await self._count_frames(interrupted_job.id)
    config.total_frames = config.total_frames - frames_captured

    # Start capture loop
    await self._start_capture_loop(
        camera_id=camera_id,
        job_id=interrupted_job.id,
        device_path=device_path,
        camera_type=camera_type,
        config=config,
        session=session,
    )

    return True, "Timelapse resumed", interrupted_job.id


async def finalize_interrupted(
    self,
    camera_id: int,
    session: AsyncSession,
    output_fps: int = 30,
) -> tuple[bool, str, int | None]:
    """Generate video from interrupted timelapse frames."""
    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        return False, "No interrupted timelapse found", None

    frame_info = await self.get_interrupted_frame_info(interrupted_job.id)
    if frame_info["frame_count"] == 0:
        return False, "No frames to process", None

    # Mark original job as completed (frames processed)
    await job_repo.update(interrupted_job.id, status="completed")

    # Generate video
    output_path = await self._generate_video(
        job_id=interrupted_job.id,
        fps=output_fps,
    )

    return True, "Video generation started", interrupted_job.id


async def cleanup_interrupted(
    self,
    camera_id: int,
    session: AsyncSession,
) -> tuple[bool, str, dict]:
    """Delete frames from interrupted timelapse."""
    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        return False, "No interrupted timelapse found", {}

    frame_info = await self.get_interrupted_frame_info(interrupted_job.id)
    frames_dir = Path(settings.TIMELAPSE_PATH) / f"job_{interrupted_job.id}"

    # Delete frames
    if frames_dir.exists():
        shutil.rmtree(frames_dir)

    # Mark job as failed/cleaned
    await job_repo.update(interrupted_job.id, status="failed", error_message="Cleaned up by user")

    return True, "Timelapse frames deleted", {
        "frames_deleted": frame_info["frame_count"],
        "space_freed_bytes": frame_info["disk_usage_bytes"],
        "space_freed_human": frame_info["disk_usage_human"],
    }
```

**Task 3: Add job repository method**

File: `backend/app/db/repositories/job.py` - Add:

```python
async def get_interrupted_timelapse(self, camera_id: int) -> Job | None:
    """Get interrupted timelapse job for camera."""
    stmt = select(Job).where(
        Job.camera_id == camera_id,
        Job.job_type == "timelapse",
        Job.status == "interrupted",
    ).order_by(Job.started_at.desc()).limit(1)

    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

---

## Frontend Implementation

### Components

```
frontend/src/components/camera/
├── TimelapseResumeBar.tsx
├── TimelapseResumeBar.css
├── TimelapseCleanupDialog.tsx
└── TimelapseCleanupDialog.css
```

### Phase 1: TimelapseResumeBar Component

File: `frontend/src/components/camera/TimelapseResumeBar.tsx`

```tsx
/**
 * Banner shown when an interrupted timelapse is detected
 */

import { Button } from "../Button";
import "./TimelapseResumeBar.css";

interface InterruptedTimelapse {
  job_id: number;
  frame_count: number;
  disk_usage_human: string;
  started_at: string;
  interrupted_at: string;
}

interface TimelapseResumeBarProps {
  interrupted: InterruptedTimelapse;
  onResume: () => void;
  onFinalize: () => void;
  onCleanup: () => void;
  loading?: boolean;
}

export function TimelapseResumeBar({
  interrupted,
  onResume,
  onFinalize,
  onCleanup,
  loading = false,
}: TimelapseResumeBarProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="timelapse-resume-bar">
      <div className="timelapse-resume-bar__icon">⚠️</div>
      <div className="timelapse-resume-bar__content">
        <div className="timelapse-resume-bar__title">
          Interrupted Timelapse Detected
        </div>
        <div className="timelapse-resume-bar__info">
          <span>{interrupted.frame_count} frames captured</span>
          <span>•</span>
          <span>{interrupted.disk_usage_human}</span>
          <span>•</span>
          <span>Started: {formatDate(interrupted.started_at)}</span>
        </div>
      </div>
      <div className="timelapse-resume-bar__actions">
        <Button
          variant="primary"
          size="sm"
          onClick={onResume}
          disabled={loading}
        >
          Resume
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={onFinalize}
          disabled={loading}
        >
          Create Video
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={onCleanup}
          disabled={loading}
        >
          Discard
        </Button>
      </div>
    </div>
  );
}
```

### Phase 2: TimelapseCleanupDialog Component

File: `frontend/src/components/camera/TimelapseCleanupDialog.tsx`

```tsx
/**
 * Dialog for confirming timelapse cleanup
 */

import { Modal } from "../Modal";
import { Button } from "../Button";
import "./TimelapseCleanupDialog.css";

interface TimelapseCleanupDialogProps {
  isOpen: boolean;
  frameCount: number;
  diskUsage: string;
  onFinalize: () => void;
  onDelete: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function TimelapseCleanupDialog({
  isOpen,
  frameCount,
  diskUsage,
  onFinalize,
  onDelete,
  onCancel,
  loading = false,
}: TimelapseCleanupDialogProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title="Cleanup Interrupted Timelapse"
      width="md"
    >
      <div className="timelapse-cleanup-dialog">
        <div className="timelapse-cleanup-dialog__info">
          <p>
            You have <strong>{frameCount} frames</strong> from an interrupted
            timelapse using <strong>{diskUsage}</strong> of disk space.
          </p>
          <p>What would you like to do?</p>
        </div>

        <div className="timelapse-cleanup-dialog__options">
          <div className="timelapse-cleanup-dialog__option">
            <h4>Create Video</h4>
            <p>Generate a timelapse video from the captured frames.</p>
            <Button
              variant="primary"
              onClick={onFinalize}
              disabled={loading}
              className="timelapse-cleanup-dialog__button"
            >
              {loading ? "Processing..." : "Create Video from Frames"}
            </Button>
          </div>

          <div className="timelapse-cleanup-dialog__divider">or</div>

          <div className="timelapse-cleanup-dialog__option timelapse-cleanup-dialog__option--danger">
            <h4>Delete Frames</h4>
            <p>
              Permanently delete all captured frames. This cannot be undone.
            </p>
            <Button
              variant="danger"
              onClick={onDelete}
              disabled={loading}
              className="timelapse-cleanup-dialog__button"
            >
              {loading ? "Deleting..." : "Delete All Frames"}
            </Button>
          </div>
        </div>

        <div className="timelapse-cleanup-dialog__actions">
          <Button variant="outline" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
```

### Phase 3: Integration with TimelapseTab

Update `frontend/src/components/camera/TimelapseTab.tsx`:

```tsx
import { TimelapseResumeBar } from "./TimelapseResumeBar";
import { TimelapseCleanupDialog } from "./TimelapseCleanupDialog";

// Add state
const [interrupted, setInterrupted] = useState<InterruptedTimelapse | null>(null);
const [showCleanupDialog, setShowCleanupDialog] = useState(false);
const [resumeLoading, setResumeLoading] = useState(false);

// Check for interrupted timelapse on mount
useEffect(() => {
  checkInterrupted();
}, [cameraId]);

const checkInterrupted = async () => {
  try {
    const { data } = await apiClient.GET(
      `/api/v1/cameras/${cameraId}/timelapse/interrupted` as any
    );
    if (data?.has_interrupted) {
      setInterrupted(data);
    } else {
      setInterrupted(null);
    }
  } catch (error) {
    console.error("Failed to check interrupted timelapse:", error);
  }
};

const handleResume = async () => {
  setResumeLoading(true);
  try {
    const { error } = await apiClient.POST(
      `/api/v1/cameras/${cameraId}/timelapse/resume` as any
    );
    if (error) throw new Error(error.detail);
    toast.success("Timelapse resumed");
    setInterrupted(null);
    setIsRunning(true);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Failed to resume");
  } finally {
    setResumeLoading(false);
  }
};

const handleFinalize = async () => {
  setResumeLoading(true);
  try {
    const { error } = await apiClient.POST(
      `/api/v1/cameras/${cameraId}/timelapse/finalize` as any
    );
    if (error) throw new Error(error.detail);
    toast.success("Video generation started");
    setInterrupted(null);
    setShowCleanupDialog(false);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Failed to finalize");
  } finally {
    setResumeLoading(false);
  }
};

const handleCleanup = async () => {
  setResumeLoading(true);
  try {
    const { error } = await apiClient.DELETE(
      `/api/v1/cameras/${cameraId}/timelapse/cleanup` as any
    );
    if (error) throw new Error(error.detail);
    toast.success("Timelapse frames deleted");
    setInterrupted(null);
    setShowCleanupDialog(false);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Failed to cleanup");
  } finally {
    setResumeLoading(false);
  }
};

// In render, at the top of the component:
{interrupted && (
  <TimelapseResumeBar
    interrupted={interrupted}
    onResume={handleResume}
    onFinalize={handleFinalize}
    onCleanup={() => setShowCleanupDialog(true)}
    loading={resumeLoading}
  />
)}

// Add cleanup dialog:
<TimelapseCleanupDialog
  isOpen={showCleanupDialog}
  frameCount={interrupted?.frame_count || 0}
  diskUsage={interrupted?.disk_usage_human || "0 B"}
  onFinalize={handleFinalize}
  onDelete={handleCleanup}
  onCancel={() => setShowCleanupDialog(false)}
  loading={resumeLoading}
/>
```

---

## CSS Styles

File: `frontend/src/components/camera/TimelapseResumeBar.css`

```css
.timelapse-resume-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
  border-radius: 8px;
  margin-bottom: 1rem;
}

.timelapse-resume-bar__icon {
  font-size: 1.5rem;
}

.timelapse-resume-bar__content {
  flex: 1;
}

.timelapse-resume-bar__title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.timelapse-resume-bar__info {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.timelapse-resume-bar__actions {
  display: flex;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .timelapse-resume-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .timelapse-resume-bar__actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
```

---

## Testing Checklist

- [ ] Interrupted timelapse detected on page load
- [ ] Resume bar displays with correct frame count and size
- [ ] Resume continues capturing from where it stopped
- [ ] Finalize generates video from existing frames
- [ ] Cleanup deletes frames and frees disk space
- [ ] Cleanup dialog shows before deletion
- [ ] Loading states during all operations
- [ ] Error handling for all operations
- [ ] Bar disappears after successful action
- [ ] WebSocket updates job status after resume

---

**Status**: `.ready.md` - Ready for implementation
