# Camera Tabs Components - Gap Analysis

## Overview

This document analyzes the gaps between the planned Camera Tabs functionality (from `ui-remaining-components.in_progress.md`) and what's currently implemented.

---

## Summary of Findings

| Component | Planned | Implemented | Gap Level |
|-----------|---------|-------------|-----------|
| CameraPage | Yes | Yes | Minor |
| CameraTabNav | Yes | Inline in CameraPage | None (different approach) |
| LivePreview | Yes | PreviewTab.tsx | **Major** |
| CaptureTab | Yes | Yes | **Medium** |
| RecordTab | Yes | Yes | **Medium** |
| TimelapseTab | Yes | Yes | **Major** |
| JobStatusDisplay | Yes | **No** | **Critical** |
| DiskSpaceWarning | Yes | Yes | Minor |
| TimelapseResumeBar | Yes | **No** | **High** |
| TimelapseCleanupDialog | Yes | **No** | **High** |
| Media Browser (files list) | Yes | **No** | **Critical** |
| Dynamic Camera Nav | Yes | **No** | **High** (separate plan exists) |

---

## Critical Gaps (Must Have)

### Gap 1: JobStatusDisplay Component - NOT IMPLEMENTED

**Planned Functionality** (from plan):
- Display current/past jobs for camera
- Fetch jobs: `GET /jobs?camera_id=:cameraId`
- Display job list: Type, status, progress, start/end time
- Subscribe to `job_update` WebSocket for real-time progress
- Progress bar for running jobs

**Current State**:
- Jobs API exists in backend (`/api/v1/jobs`)
- WebSocket `job_update` messages are handled in RecordTab/TimelapseTab individually
- **No centralized JobStatusDisplay component**
- **No job history visible to user**

**Impact**: Users cannot see:
- History of recordings/timelapses
- Failed job details
- Currently running jobs across all cameras

**Recommended Implementation**:
```
frontend/src/components/camera/JobStatusDisplay.tsx
frontend/src/components/camera/JobStatusDisplay.css
```

---

### Gap 2: Media Browser (Files List) - NOT IMPLEMENTED

**Planned Functionality** (from plan):
- `GET /files/recordings?camera_id=:cameraId` - List recordings
- `GET /files/timelapses?camera_id=:cameraId` - List timelapses
- Display: Filename, duration, size, timestamp
- Actions: Play (video player modal), Download, Delete
- Pagination: Last 10 videos, load more

**Current State**:
- **No files API in backend**
- **No files list UI in frontend**
- RecordTab/TimelapseTab show only current operation status
- Captured images show last capture only, no history

**Impact**: Users cannot:
- Browse recorded videos
- Download recordings
- Play back recordings in browser
- Delete old recordings
- See timelapse output videos
- Manage storage by deleting old files

**Recommended Implementation**:

Backend:
```
backend/app/api/routes/files.py
  - GET /api/v1/files/recordings
  - GET /api/v1/files/stills
  - GET /api/v1/files/timelapses
  - GET /api/v1/files/{file_id}/download
  - DELETE /api/v1/files/{file_id}
```

Frontend:
```
frontend/src/components/camera/MediaBrowser.tsx
frontend/src/components/camera/VideoPlayer.tsx (modal)
```

---

## High Priority Gaps

### Gap 3: Timelapse Resume/Cleanup - NOT IMPLEMENTED

**Planned Functionality** (from plan):
- Detect interrupted timelapses on page load
- Show resume banner: "Interrupted timelapse detected. Resume or cleanup?"
- Resume button: `POST /cameras/:cameraId/timelapse/resume`
- Cleanup dialog with options:
  - "Keep frames and generate video"
  - "Delete all frames"
- Finalize endpoint: `POST /cameras/:cameraId/timelapse/finalize`

**Current State**:
- TimelapseTab has start/stop only
- No resume detection
- No cleanup UI
- Backend may or may not support resume (needs verification)

**Impact**: If timelapse is interrupted (power outage, network issue):
- User loses all captured frames
- No way to generate video from partial capture
- No way to clean up orphaned frames

**Recommended Implementation**:
```
frontend/src/components/camera/TimelapseResumeBar.tsx
frontend/src/components/camera/TimelapseCleanupDialog.tsx
```

Backend (verify/add):
```
POST /api/v1/cameras/{camera_id}/timelapse/resume
POST /api/v1/cameras/{camera_id}/timelapse/finalize
```

---

### Gap 4: Dynamic Camera Navigation - NOT IMPLEMENTED

**Status**: Separate plan exists (`dynamic-camera-navigation.ready.md`)

**Summary**: Layout.tsx needs to fetch cameras and render dynamic tabs.

---

## Medium Priority Gaps

### Gap 5: Preview Tab - Stream URL Hardcoded

**Issue**: PreviewTab.tsx line 57-60:
```typescript
const getStreamUrl = () => {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  return `${baseUrl}/api/v1/cameras/${cameraId}/preview/stream`;
};
```

**Problem**: Uses `http://localhost:8000` fallback instead of relative URL. This will fail in production (same issue we just fixed in apiClient).

**Fix**: Change to relative URL:
```typescript
const getStreamUrl = () => {
  return `/api/v1/cameras/${cameraId}/preview/stream`;
};
```

---

### Gap 6: CaptureTab - Image URL Hardcoded

**Issue**: CaptureTab.tsx line 51:
```typescript
const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const imageUrl = `${baseUrl}${(data as any).file_url}`;
```

**Problem**: Same hardcoded URL issue.

**Fix**: Use relative URL for captured images.

---

### Gap 7: Capture Tab - Missing Features

**Planned but missing**:
- Format selector: JPEG/PNG (only quality is implemented)
- Recent captures list (last 5)
- Only shows last captured image

**Current State**:
- Quality selector works
- Capture button works
- Only shows single last capture

---

### Gap 8: Record Tab - Missing Recording History

**Planned but missing**:
- Display recorded videos list
- Play/Download/Delete actions
- Resolution/FPS selectors (only bitrate implemented)

**Current State**:
- Bitrate selector works
- Duration timer works
- Start/Stop works
- **No history of recordings visible**

---

### Gap 9: Timelapse Tab - Missing Video List

**Planned but missing**:
- Display completed timelapse videos list
- Play/Download/Delete actions
- Last frame preview during capture

**Current State**:
- Interval/Duration settings work
- Progress display works
- **No history of completed timelapses**
- **No preview of captured frames**

---

## Minor Gaps

### Gap 10: Preview Auto-Reconnect

**Planned**: Auto-reconnect with exponential backoff (1s, 2s, 4s, max 10s)

**Current**: Manual "Reconnect" button on error

**Recommendation**: Lower priority, manual reconnect is acceptable for MVP.

---

### Gap 11: Encoder Busy (409) Handling

**Planned**: Show which camera has the encoder when 409 conflict occurs

**Current**: Generic error message

**Current code** (RecordTab.tsx):
```typescript
if (error) {
  const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to start recording";
  throw new Error(errorMessage);
}
```

**Recommendation**: Backend should return which camera has encoder in 409 response. Frontend should display helpful message.

---

## Backend API Gaps

### Missing Endpoints

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `GET /api/v1/files/recordings` | List recording files | Critical |
| `GET /api/v1/files/stills` | List captured images | Critical |
| `GET /api/v1/files/timelapses` | List timelapse videos | Critical |
| `GET /api/v1/files/{id}` | Download file | Critical |
| `DELETE /api/v1/files/{id}` | Delete file | Critical |
| `POST /api/v1/cameras/{id}/timelapse/resume` | Resume interrupted timelapse | High |
| `POST /api/v1/cameras/{id}/timelapse/finalize` | Generate video from frames | High |
| `GET /api/v1/system/disk` | Get accurate disk stats | Medium |

---

## Recommended Implementation Order

### Phase 1: Quick Fixes (Same Day)
1. Fix hardcoded URLs in PreviewTab.tsx and CaptureTab.tsx
2. Implement dynamic camera navigation (plan exists)

### Phase 2: Critical Functionality (1-2 days)
3. Backend: Files API (list, download, delete)
4. Frontend: MediaBrowser component
5. Frontend: JobStatusDisplay component
6. Integrate MediaBrowser into RecordTab/TimelapseTab/CaptureTab

### Phase 3: Timelapse Recovery (1 day)
7. Backend: Timelapse resume/finalize endpoints
8. Frontend: TimelapseResumeBar component
9. Frontend: TimelapseCleanupDialog component

### Phase 4: Polish (Optional)
10. Preview auto-reconnect
11. Better encoder conflict messages
12. Format selector in CaptureTab
13. Resolution/FPS selectors in RecordTab

---

## File Structure for New Components

```
frontend/src/components/camera/
├── CaptureTab.tsx (exists - needs url fix)
├── CaptureTab.css
├── DiskSpaceWarning.tsx (exists)
├── DiskSpaceWarning.css
├── JobStatusDisplay.tsx (NEW)
├── JobStatusDisplay.css (NEW)
├── MediaBrowser.tsx (NEW)
├── MediaBrowser.css (NEW)
├── PreviewTab.tsx (exists - needs url fix)
├── PreviewTab.css
├── RecordTab.tsx (exists)
├── RecordTab.css
├── TimelapseTab.tsx (exists)
├── TimelapseTab.css
├── TimelapseResumeBar.tsx (NEW)
├── TimelapseResumeBar.css (NEW)
├── TimelapseCleanupDialog.tsx (NEW)
├── TimelapseCleanupDialog.css (NEW)
└── VideoPlayer.tsx (NEW - modal for playback)

backend/app/api/routes/
├── files.py (NEW)
└── ... (existing)
```

---

## Questions for Review

1. **Priority**: Should we implement Files API + MediaBrowser first, or JobStatusDisplay first?

2. **Timelapse Resume**: Is timelapse resume functionality supported in the backend? Need to verify before frontend work.

3. **Video Playback**: Should video playback be in-browser (HTML5 video) or download-only?

4. **Storage Location**: Where are media files stored? Need path for Files API implementation.

5. **File Retention**: Should Files API include automatic cleanup based on retention settings from OutputConfig?

---

**Status**: `.ready.md` - Gap analysis complete, ready for prioritization
