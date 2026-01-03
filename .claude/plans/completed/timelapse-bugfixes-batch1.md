# Timelapse Bugfixes - Batch 1

**Status**: Completed
**Priority**: Medium to Low
**Scope**: 3 bugs related to progress reporting and job lifecycle
**Completed**: 2026-01-03

---

## Bug 1: Progress Reporting Mismatch (Medium Priority)

### Problem Statement

The frontend assumes WebSocket `progress` is a percentage (0-100) and calculates frames using flawed math:

**File**: [TimelapseTab.tsx:51-57](frontend/src/components/camera/TimelapseTab.tsx#L51-L57)

```typescript
if (message.progress !== null && message.progress !== undefined) {
  // Progress is 0-100, convert to frames
  const totalFramesEstimate = totalFrames || 100;
  const capturedFrames = Math.floor(
    (message.progress / 100) * totalFramesEstimate
  );
  setFramesCaptured(capturedFrames);
}
```

### Root Cause Analysis

1. **Assumption mismatch**: Frontend assumes `progress` is a percentage, but the backend's `get_timelapse_progress()` returns `(current_frame, total_frames)` tuple
2. **Fallback breaks unlimited timelapses**: When `totalFrames=0` (unlimited), falls back to 100 which gives meaningless percentages
3. **State dependency**: `totalFrames` state comes from user input, not from server's actual config - they can diverge

### Impact

- Progress bar shows incorrect percentages
- Unlimited timelapses show nonsensical progress (e.g., "150% complete")
- User confusion about actual capture status

### Correction

#### Step 1: Extend WebSocket job_update message to include frame counts

**File**: `backend/app/services/websocket.py` (or wherever job_update messages are broadcast)

Add `current_frame` and `total_frames` fields to job_update messages for timelapse jobs:

```python
# When broadcasting timelapse job updates, include frame info
message = {
    "type": "job_update",
    "job_type": "timelapse",
    "camera_id": camera_id,
    "status": status,
    "progress": progress,  # Keep for backwards compatibility
    "current_frame": current_frame,  # NEW
    "total_frames": total_frames,    # NEW (None for unlimited)
}
```

#### Step 2: Update WSJobUpdate TypeScript type

**File**: `frontend/src/types/websocket.ts`

```typescript
export interface WSJobUpdate {
  camera_id: number;
  job_type: string;
  status: string;
  progress: number | null;
  current_frame?: number;      // NEW
  total_frames?: number | null; // NEW (null = unlimited)
}
```

#### Step 3: Update frontend to use frame counts directly

**File**: [TimelapseTab.tsx:47-73](frontend/src/components/camera/TimelapseTab.tsx#L47-L73)

```typescript
useWebSocketMessage<WSJobUpdate>(wsClient, "job_update", (message) => {
  if (message.camera_id === cameraId && message.job_type === "timelapse") {
    if (message.status === "running") {
      setIsRunning(true);
      // Use frame counts directly if available
      if (message.current_frame !== undefined) {
        setFramesCaptured(message.current_frame);
      }
      if (message.total_frames !== undefined && message.total_frames !== null) {
        setTotalFrames(message.total_frames);
      }
    } else if (message.status === "completed" || message.status === "failed" || message.status === "interrupted") {
      // ... existing code
    }
  }
});
```

#### Step 4: Handle unlimited timelapses in progress display

**File**: [TimelapseTab.tsx:267-268](frontend/src/components/camera/TimelapseTab.tsx#L267-L268)

```typescript
// Handle unlimited timelapse (totalFrames = 0 or null)
const progressPercent = totalFrames && totalFrames > 0
  ? (framesCaptured / totalFrames) * 100
  : 0;
const isUnlimited = !totalFrames || totalFrames === 0;
```

Update the display at lines 349-361 to show "X frames captured" for unlimited timelapses instead of percentage.

### Testing

1. Start a timelapse with 10 frames, verify progress bar updates correctly via WebSocket
2. Start an unlimited timelapse (duration=0), verify it shows frame count without percentage
3. Verify progress survives page refresh by checking status endpoint
4. Test with different intervals (1s, 60s) to ensure timing doesn't affect accuracy

---

## Bug 2: Job `completed_at` Not Set on Manual Stop (Low Priority)

### Problem Statement

When a user stops a timelapse with `assemble_video=False`, the job is marked as `status=completed` but `completed_at` timestamp remains NULL.

**File**: [service.py:210-219](backend/app/services/camera/timelapse/service.py#L210-L219)

```python
# Update job status
if session and job_id:
    job_repo = JobRepository(session)
    if output_path:
        await job_repo.mark_completed(job_id, output_path)  # Sets completed_at
    elif frame_count > 0:
        await job_repo.mark_completed(job_id, str(timelapse_dir))  # Sets completed_at
    else:
        await job_repo.mark_interrupted(job_id)  # Does NOT set completed_at
    await session.commit()
```

### Root Cause Analysis

The `mark_interrupted()` method doesn't set `completed_at`, which is correct for interrupted jobs. However, when `frame_count > 0` but `assemble_video=False`, the job IS completed (user intentionally stopped it), but the code path goes through `mark_completed()` which DOES set `completed_at`.

**Actual Bug Location**: Looking more carefully, the real issue is that `mark_completed()` is called correctly. Let me re-examine...

After re-reading: The bug is actually when `frame_count == 0` - the job is marked as interrupted, but if the user intentionally stopped it (vs. system crash), it should arguably be "completed" with 0 frames.

**Revised Understanding**: The current logic is:
- `output_path` exists → `mark_completed` ✓
- `frame_count > 0` → `mark_completed` ✓
- `frame_count == 0` → `mark_interrupted` ← This may be wrong for intentional stops

### Correction

The current behavior is actually reasonable: if no frames were captured, treating it as "interrupted" makes sense. However, for clarity and data integrity, we should ensure `completed_at` is set whenever the user intentionally stops (vs. system crash).

**File**: [service.py:210-219](backend/app/services/camera/timelapse/service.py#L210-L219)

```python
# Update job status
if session and job_id:
    job_repo = JobRepository(session)
    if output_path:
        await job_repo.mark_completed(job_id, output_path)
    elif frame_count > 0:
        await job_repo.mark_completed(job_id, str(timelapse_dir))
    else:
        # User intentionally stopped with 0 frames - mark as completed, not interrupted
        await job_repo.mark_completed(job_id, None)
    await session.commit()
```

Also verify `mark_completed()` in JobRepository handles `output_path=None`:

**File**: `backend/app/db/repositories/job.py`

```python
async def mark_completed(self, job_id: int, output_path: str | None = None) -> None:
    """Mark job as completed with optional output path."""
    await self.update(
        job_id,
        status="completed",
        completed_at=datetime.utcnow(),
        output_path=output_path,
    )
```

### Testing

1. Start timelapse, immediately stop (0 frames) - verify `status=completed`, `completed_at` is set
2. Start timelapse, capture 5 frames, stop without video - verify `completed_at` is set
3. Start timelapse, capture frames, stop with video - verify `completed_at` is set
4. Simulate crash (kill process) - verify job shows as `interrupted` with `completed_at=NULL`

---

## Bug 3: WebSocket Progress Not Broadcast (Low Priority)

### Problem Statement

The `update_job_progress()` method writes frame count to database but doesn't broadcast a WebSocket update. Frontend only gets progress via periodic job_update messages or polling.

**File**: [service.py:540-564](backend/app/services/camera/timelapse/service.py#L540-L564)

```python
async def update_job_progress(
    self, camera_id: int, session: AsyncSession
) -> bool:
    """Update job progress in database."""
    if camera_id not in self._sessions:
        return False

    timelapse_session = self._sessions[camera_id]
    job_id = timelapse_session.job_id

    if not job_id:
        return False

    job_repo = JobRepository(session)
    await job_repo.update_timelapse_progress(job_id, timelapse_session.frame_count)
    await session.commit()
    return True
    # BUG: No WebSocket broadcast here!
```

### Root Cause Analysis

The method updates the database but has no mechanism to push updates to connected WebSocket clients. The frontend must either:
1. Poll the `/timelapse/status` endpoint
2. Wait for periodic `job_update` broadcasts (if they exist)

Neither provides real-time frame-by-frame updates.

### Correction

#### Step 1: Add WebSocket broadcast after database update

**File**: [service.py:540-564](backend/app/services/camera/timelapse/service.py#L540-L564)

```python
async def update_job_progress(
    self, camera_id: int, session: AsyncSession
) -> bool:
    """Update job progress in database and broadcast via WebSocket."""
    if camera_id not in self._sessions:
        return False

    timelapse_session = self._sessions[camera_id]
    job_id = timelapse_session.job_id

    if not job_id:
        return False

    current_frame, total_frames = timelapse_session.get_progress()

    # Update database
    job_repo = JobRepository(session)
    await job_repo.update_timelapse_progress(job_id, current_frame)
    await session.commit()

    # Broadcast WebSocket update
    from app.services.websocket import ws_manager  # Import here to avoid circular
    await ws_manager.broadcast_job_update(
        camera_id=camera_id,
        job_type="timelapse",
        job_id=job_id,
        status="running",
        current_frame=current_frame,
        total_frames=total_frames,
    )

    return True
```

#### Step 2: Add broadcast_job_update method to WebSocket manager

**File**: `backend/app/services/websocket.py`

```python
async def broadcast_job_update(
    self,
    camera_id: int,
    job_type: str,
    job_id: int,
    status: str,
    current_frame: int | None = None,
    total_frames: int | None = None,
) -> None:
    """Broadcast job update to all connected clients."""
    message = {
        "type": "job_update",
        "camera_id": camera_id,
        "job_type": job_type,
        "job_id": job_id,
        "status": status,
        "progress": (current_frame / total_frames * 100) if total_frames else None,
        "current_frame": current_frame,
        "total_frames": total_frames,
    }
    await self.broadcast(message)
```

#### Step 3: Call update_job_progress from capture loop

The capture loop should call this method after each successful frame capture.

**File**: [session.py:386-407](backend/app/services/camera/timelapse/session.py#L386-L407) - `_handle_capture_success()` method

This requires the capture loop to have access to a database session, which it currently doesn't. Options:

**Option A** (Recommended): Emit an event that the API layer can listen to and broadcast
**Option B**: Pass a callback function to the session for progress updates
**Option C**: Use a background task that periodically syncs progress

For simplicity, **Option B** - add an async callback:

**File**: [session.py:43-54](backend/app/services/camera/timelapse/session.py#L43-L54)

```python
class TimelapseSession:
    def __init__(
        self,
        config: TimelapseConfig,
        device_path: str,
        camera_type: str,
        job_id: int | None,
        timelapse_dir: Path,
        hardware_id: str | None = None,
        device_resolver: Callable[[str], str | None] | None = None,
        target_end_time: datetime | None = None,
        polling_service: "EnvironmentPollingService | None" = None,
        on_frame_captured: Callable[[int, int | None], Awaitable[None]] | None = None,  # NEW
    ):
        # ... existing init
        self._on_frame_captured = on_frame_captured
```

Then in `_handle_capture_success()`:

```python
async def _handle_capture_success(self, filepath: str | None) -> None:
    """Handle successful frame capture."""
    # ... existing code ...
    self.frame_count += 1

    # Notify callback if registered
    if self._on_frame_captured:
        await self._on_frame_captured(self.frame_count, self.config.total_frames)
```

Then in `start_timelapse()` in service.py, pass a callback that broadcasts via WebSocket.

### Testing

1. Open browser dev tools Network tab, filter for WebSocket
2. Start timelapse with 5 second interval
3. Verify `job_update` messages arrive every 5 seconds with incrementing `current_frame`
4. Verify frontend progress bar updates in real-time without polling
5. Test with multiple browser tabs - all should receive updates

---

## Implementation Order

1. **Bug 1** (Progress Reporting) - Highest impact, affects user experience
2. **Bug 3** (WebSocket Broadcast) - Enables real-time updates, builds on Bug 1 changes
3. **Bug 2** (completed_at) - Lowest impact, data consistency fix

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/camera/timelapse/service.py` | Bugs 2, 3 |
| `backend/app/services/camera/timelapse/session.py` | Bug 3 (callback) |
| `backend/app/services/websocket.py` | Bugs 1, 3 |
| `backend/app/db/repositories/job.py` | Bug 2 (verify) |
| `frontend/src/types/websocket.ts` | Bug 1 |
| `frontend/src/components/camera/TimelapseTab.tsx` | Bug 1 |
