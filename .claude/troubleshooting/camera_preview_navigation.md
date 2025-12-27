# Camera Preview Navigation Issue - Troubleshooting Log

**Issue**: Camera previews stop displaying after navigating between camera pages
**First Reported**: 2025-12-26
**Status**: IN PROGRESS - Architectural issues identified

---

## Symptoms

1. Camera previews work initially after hard refresh (Ctrl+F5)
2. User navigates to individual camera pages (e.g., `/camera/1`, `/camera/4`)
3. After returning to dashboard, camera previews no longer display
4. Sometimes individual camera pages show "Preview not running" when preview IS running
5. Page occasionally freezes completely during navigation
6. 499 errors (client closed connection) appear in nginx logs during navigation

## Environment

- Frontend: React + Vite, served from `/opt/timemachine/static/`
- Backend: FastAPI on port 8000
- Kiosk: Chromium in kiosk mode on Raspberry Pi
- Streams: GStreamer MJPEG via TCP (`tcpserversink`), proxied through FastAPI `/api/v1/cameras/{id}/preview/stream`

---

## Root Cause Analysis (2025-12-26 20:20)

### Architecture Overview

```
Dashboard (HomePage)                    Camera Page
    │                                       │
    ├─ CameraPreviewCard (x3)              ├─ PreviewTab
    │   └─ LiveThumbnail                   │   └─ <img> with MJPEG
    │       └─ <img> with MJPEG            │
    │                                       │
    └─ useCameraDashboard hook             └─ Auto-start preview
        └─ Watchdog (auto-starts previews)
```

### The Core Problem: Multiple Competing Stream Consumers

The system has **TWO independent components** trying to manage the same camera preview streams:

1. **Dashboard Watchdog** (`useCameraDashboard.ts:181-221`)
   - Polls every 5 seconds
   - Auto-starts previews for idle cameras
   - Uses exponential backoff for failed starts

2. **PreviewTab** (`PreviewTab.tsx:354-365`)
   - Auto-starts preview on mount (when `autoStart=true`)
   - Checks preview status then calls `startPreviewWithRetry()`

These can race and conflict, especially during navigation.

### Issue 1: TCP Socket Contention (Backend)

**Location**: `backend/app/services/camera/preview.py`

GStreamer's `tcpserversink` allows multiple clients, but:
- Each client gets the SAME stream position
- When one client disconnects mid-frame, buffer state can corrupt
- The FastAPI stream generator may not terminate cleanly on 499

**Impact**: When browser navigates away, the async generator keeps trying to send data to a closed connection.

### Issue 2: Connection Exhaustion During Rapid Navigation

**Pattern**: home → camera1 → home → camera2 → home (rapid clicking)

Each navigation:
1. Creates new `<img>` element with MJPEG src
2. Browser opens new HTTP connection
3. Previous connection may not close immediately
4. Backend stream generators accumulate
5. Eventually, TCP connections exhaust or GStreamer buffers overflow

### Issue 3: React Component Lifecycle + Async Operations

**LiveThumbnail** (`LiveThumbnail.tsx:83-110`):
- Clears `imgRef.current.src = ""` on unmount to stop stream
- But async error handlers may still fire after unmount
- `mountedRef` check helps but isn't bulletproof

**PreviewTab** (`PreviewTab.tsx:354-371`):
- Has `startPreviewWithRetry` in useEffect dependencies (problematic)
- Fixed with ref pattern but dependency array still has issues
- Does NOT stop preview on unmount (by design, but causes issues)

### Issue 4: Stale useEffect Dependencies

**PreviewTab.tsx:354-371**:
```tsx
useEffect(() => {
  // ... initializePreview
}, [checkPreviewStatus, autoStart, autoStartAttempted, checkForActiveObservation]);
```

Many of these callbacks (`checkPreviewStatus`, `checkForActiveObservation`) depend on `cameraId`, which causes them to change on every render when navigating between cameras. This triggers effect re-runs unpredictably.

---

## Changes Made (2025-12-26)

### Fix Attempt 1: Key-based Remount (17:50)
- Changed `LiveThumbnail` key to include `refreshKey`
- Added `navigationKey` from `useLocation().key` in HomePage
- **Result**: Helped with stale error state but didn't fix connection issues

### Fix Attempt 2: Remove Unmount Cleanup (19:30)
- Removed `PreviewTab` cleanup effect that stopped previews on unmount
- **Rationale**: Dashboard watchdog manages previews, stopping on unmount causes dashboard feeds to disappear
- **Result**: Partially helped but camera pages now don't show preview

### Fix Attempt 3: Use Ref for startPreviewWithRetry (19:45)
- Added `startPreviewRef` to avoid function in useEffect dependencies
- **Result**: Reduced effect re-runs but issue persists

### Additional Changes
- `refresh-kiosk.sh` now clears browser cache
- Removed debug console.log statements

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/LiveThumbnail.tsx` | Key includes refreshKey, removed debug logs |
| `frontend/src/components/CameraPreviewCard.tsx` | Key includes refreshKey, removed debug logs |
| `frontend/src/pages/HomePage.tsx` | Uses `useLocation().key` for navigationKey |
| `frontend/src/components/camera/PreviewTab.tsx` | Removed unmount cleanup, added startPreviewRef |
| `scripts/refresh-kiosk.sh` | Clears browser cache before starting |

---

## Recommended Architectural Fixes

### Short-term Fixes

1. **Single Source of Truth for Preview State**
   - Either dashboard watchdog OR PreviewTab should manage previews, not both
   - Recommended: Dashboard watchdog handles starts, PreviewTab just displays

2. **Add AbortController for Navigation**
   - When navigating away, explicitly abort pending fetch/stream operations
   - Prevent race conditions with in-flight requests

3. **Backend Connection Cleanup**
   - Add client tracking to stream endpoint
   - Force-close stale connections after timeout
   - Use `asyncio.wait_for` with reasonable timeouts

### Long-term Fixes

1. **Shared Stream Context**
   - Create a React context that manages camera streams globally
   - Components subscribe to streams rather than creating their own connections
   - Single HTTP connection per camera, shared across components

2. **WebSocket for State Coordination**
   - Use WebSocket to push preview state changes
   - Eliminate polling (currently 5s interval)
   - More responsive and less error-prone

3. **Backend Stream Multiplexing**
   - Instead of multiple clients connecting to GStreamer directly
   - Have a single server-side connection that broadcasts to clients
   - This prevents TCP buffer corruption from multiple consumers

---

## Current State (2025-12-26 20:20)

- Streams work after hard refresh
- Navigation still causes intermittent failures
- Page freezes still occur occasionally
- 499 errors during navigation indicate connection cleanup issues

---

## Fix Applied (2025-12-27 01:30) - SUPERSEDED

### Single Source of Truth for Preview Management

**Root cause addressed**: Multiple competing stream consumers (Dashboard Watchdog + PreviewTab auto-start)

**Change made**:
- `CameraPage.tsx` now passes `autoStart={false}` to PreviewTab
- Dashboard watchdog remains the ONLY component that starts previews
- PreviewTab only displays streams, does not auto-start them

**Note**: This fix was insufficient - user reported issue persisting. See final fix below.

---

## FINAL FIX (2025-12-26 ~23:00) - RESOLVED

### Root Cause: Browser Connection Pooling

**Discovery**: User observed that clicking the browser Stop button always fixed the issue, but React navigation caused streams to break. Browser refresh worked fine, but clicking "Home" repeatedly broke streams.

**Root cause**: MJPEG streams are long-lived HTTP connections. Browsers have a connection limit (~6 per domain). When React navigates away from a page:
1. The `<img>` element is removed from the DOM
2. But the underlying HTTP connection may not close immediately
3. Browser connection pool becomes exhausted with stale connections
4. New page mounts but can't establish new connections
5. Clicking browser Stop button forcefully aborts all connections, freeing the pool

**User observations that confirmed diagnosis**:
- "clicking stop and I see retry in the live feeds - then the live feeds recover"
- "if I just click refresh in the browser over and over and over again... I never hit the issue"
- "I can experience this issue in one browser and not another on another system"

### Final Fix: `window.stop()` on Component Cleanup

**Solution**: Call `window.stop()` in the LiveThumbnail cleanup function. This mimics the browser Stop button and forcefully aborts all pending network requests.

**Code change** (`LiveThumbnail.tsx`):
```tsx
useEffect(() => {
  // ... setup code ...

  return () => {
    mountedRef.current = false;
    window.clearTimeout(mountDelay);
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (imgRef.current) {
      imgRef.current.src = "";
    }
    setImgMounted(false);

    // Call window.stop() to forcefully abort ALL pending network requests
    // This mimics clicking the browser Stop button which reliably fixes the issue
    window.stop();
  };
}, [streamUrl, refreshKey]);
```

**Additional fixes applied during investigation**:
1. Component key includes `navigationKey` (from `useLocation().key`) to force remounts
2. Mount delay (500ms) gives browser time to close previous connections
3. Timestamp in stream URL prevents cache reuse
4. `imgMounted` state controls DOM presence to ensure clean unmount/remount
5. PreviewTab treats "already running" as success instead of error

**Files modified**:
- `frontend/src/components/LiveThumbnail.tsx` - window.stop() cleanup
- `frontend/src/pages/HomePage.tsx` - navigationKey in component keys
- `frontend/src/components/CameraPreviewCard.tsx` - refreshKey prop
- `frontend/src/components/camera/PreviewTab.tsx` - "already running" handling

**Why window.stop() works**:
- Forces browser to immediately abort ALL pending HTTP requests
- Frees up connection pool slots for new requests
- Same behavior as manually clicking the browser Stop button
- Note: This is aggressive and stops ALL requests, not just MJPEG streams

**Result**: Camera previews now recover reliably when navigating between pages.

---

## Summary of All Attempted Fixes

| # | Fix | Result |
|---|-----|--------|
| 1 | Key-based remount with refreshKey | Helped with stale state, not connections |
| 2 | Remove unmount cleanup in PreviewTab | Dashboard feeds disappeared |
| 3 | Use ref for startPreviewWithRetry | Reduced re-renders, issue persisted |
| 4 | autoStart={false} on CameraPage | Broke camera page previews |
| 5 | Mount timestamp in stream URL | Cache busting helped, issue persisted |
| 6 | imgMounted state for DOM control | Cleaner unmount, issue persisted |
| 7 | 500ms mount delay | Gave browser time, issue persisted |
| 8 | Treat "already running" as success | Fixed false errors in PreviewTab |
| 9 | **window.stop() on cleanup** | **FIXED - streams recover reliably** |

---

## Lessons Learned

1. **MJPEG streams are special**: They're long-lived HTTP connections that don't behave like typical requests
2. **Browser connection limits matter**: 6 connections per domain can be exhausted by stale MJPEG streams
3. **React cleanup isn't enough**: Setting `img.src = ""` doesn't immediately close the HTTP connection
4. **User observations are key**: "Clicking Stop fixes it" led directly to the `window.stop()` solution
5. **Cross-browser behavior varies**: Connection pool behavior differs between browsers/systems
