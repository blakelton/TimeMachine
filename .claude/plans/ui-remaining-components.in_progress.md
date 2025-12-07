# Feature: Remaining UI Components - System Settings and Camera Tabs

## Overview
This plan implements the remaining frontend UI components for TimeMachine Phase 3: System Settings page (Steps 3.12-3.16) and Camera Tabs page (Steps 3.17-3.26). These components provide comprehensive camera management, live preview, recording controls, timelapse management, and job tracking capabilities.

## Requirements

### Functional Requirements
- FR1: System Settings page with tabbed/sidebar navigation for Cameras, Output, Notifications, and Temperature panels
- FR2: Cameras CRUD panel with add/edit/delete functionality, integrated with backend API
- FR3: Output configuration panel for storage paths and retention policies
- FR4: Notification settings panel for browser notification preferences
- FR5: Temperature stub panel placeholder for future GPIO integration
- FR6: Dynamic camera navigation that updates when cameras are added/removed
- FR7: Per-camera view with live preview, capture, record, and timelapse controls
- FR8: Live MJPEG preview component with error handling and reconnection
- FR9: Capture tab with quality settings and image format selection
- FR10: Record tab with bitrate settings and disk space warnings
- FR11: Timelapse tab with interval settings, resume capability, and cleanup UI
- FR12: Job integration tracking recording/timelapse jobs in UI
- FR13: Toast notification system for operation feedback
- FR14: Disk space warning system in record/timelapse UI

### Non-Functional Requirements
- NFR1: Mobile-responsive design with hamburger menu on small screens
- NFR2: Accessible UI following WCAG 2.1 AA guidelines
- NFR3: Real-time updates via WebSocket integration
- NFR4: Form validation with clear error messages
- NFR5: Optimistic UI updates with rollback on error
- NFR6: Component reusability following DRY principles
- NFR7: Type safety using TypeScript strict mode
- NFR8: Performance: <100ms UI response time for interactions
- NFR9: Network resilience: graceful degradation when API unavailable
- NFR10: Memory efficiency: lazy load camera previews

### Success Criteria
- All CRUD operations on cameras work correctly with backend API
- Output configuration persists and applies to recording/timelapse operations
- Browser notifications trigger on recording/timelapse completion (when enabled)
- Camera tabs dynamically update when cameras are added/removed
- Live preview streams display with <500ms latency
- Disk space warnings appear when <500MB free space
- Interrupted timelapses can be resumed or cleaned up
- All forms validate input client-side before API submission
- Toast notifications provide clear feedback for all operations
- UI remains responsive during long-running operations (recording, timelapse)

## Architectural Analysis

### Existing Components Affected
- **Layout.tsx**: Navigation needs update to include dynamic camera tabs
  - Current: Static links for Home and System
  - Required: Dynamic camera navigation links, mobile hamburger menu
  - Integration: Subscribe to cameras query, update nav on changes

- **HomePage.tsx**: Quick actions need navigation to camera tabs
  - Current: Non-functional action buttons
  - Required: Link quick actions to specific camera tabs/operations
  - Integration: Pass camera context when navigating

- **App.tsx**: Routes need extension for camera tabs
  - Current: Routes for `/` and `/system`
  - Required: Dynamic route for `/camera/:cameraId` with nested tabs
  - Integration: React Router nested routing

### New Components Required

#### System Settings Components
- **SystemPage (enhanced)**: Main settings layout with sidebar navigation
  - Purpose: Container for all settings panels
  - Responsibilities: Tab state management, responsive layout
  - Why separate: Settings is a distinct feature area

- **SettingsSidebar**: Left sidebar navigation for settings sections
  - Purpose: Navigation between Cameras, Output, Notifications, Temperature
  - Responsibilities: Active section highlighting, mobile collapse
  - Why separate: Reusable navigation pattern

- **CamerasPanel**: Camera CRUD management panel
  - Purpose: Add/edit/delete cameras, view camera list
  - Responsibilities: Form handling, API integration, validation
  - Why separate: Complex form logic, substantial business logic

- **OutputPanel**: Storage and retention configuration
  - Purpose: Configure output paths and retention policies
  - Responsibilities: Path validation, disk space display
  - Why separate: Distinct configuration domain

- **NotificationsPanel**: Browser notification preferences
  - Purpose: Enable/disable notifications, configure notification types
  - Responsibilities: Permission requests, preference persistence
  - Why separate: Browser API integration, separate concern

- **TemperaturePanel**: Placeholder for future temperature control
  - Purpose: Display stub UI for GPIO temperature control
  - Responsibilities: Show coming soon message, prepare API contract
  - Why separate: Future feature isolation

#### Camera Tabs Components
- **CameraPage**: Main camera view container
  - Purpose: Layout for single camera with tab navigation
  - Responsibilities: Camera data loading, tab state management
  - Why separate: Per-camera feature container

- **CameraTabNav**: Navigation bar for Capture/Record/Timelapse tabs
  - Purpose: Switch between camera operation modes
  - Responsibilities: Active tab highlighting, tab state
  - Why separate: Reusable tab navigation pattern

- **LivePreview**: MJPEG stream display component
  - Purpose: Display live camera feed
  - Responsibilities: Stream connection, error handling, reconnection
  - Why separate: Complex streaming logic, performance critical

- **CaptureTab**: Still image capture controls
  - Purpose: Capture single images with quality settings
  - Responsibilities: Capture trigger, quality selection, image download
  - Why separate: Distinct operation mode

- **RecordTab**: Video recording controls
  - Purpose: Start/stop recording with bitrate settings
  - Responsibilities: Recording state, disk warnings, duration display
  - Why separate: Stateful recording logic, encoder constraints

- **TimelapseTab**: Timelapse scheduling and management
  - Purpose: Start/stop/resume timelapse, configure interval
  - Responsibilities: Timelapse state, interruption recovery, cleanup
  - Why separate: Complex state machine, job integration

- **JobStatusDisplay**: Job progress and status component
  - Purpose: Display current/past jobs for camera
  - Responsibilities: Job list, progress bars, job actions
  - Why separate: Reusable across tabs, WebSocket integration

#### Shared/Common Components
- **FormField**: Reusable form field wrapper
  - Purpose: Consistent form field layout with label/error
  - Responsibilities: Field layout, error display, accessibility
  - Why separate: DRY form components

- **Modal**: Generic modal dialog
  - Purpose: Reusable modal for confirmations, forms
  - Responsibilities: Overlay, focus trap, escape handling
  - Why separate: Reusable across app

- **Toast**: Toast notification component
  - Purpose: Display transient notifications
  - Responsibilities: Auto-dismiss, stacking, animation
  - Why separate: Global notification system

- **DiskSpaceWarning**: Warning banner for low disk space
  - Purpose: Alert user when disk space low
  - Responsibilities: Threshold display, warning severity
  - Why separate: Reusable across record/timelapse

- **ConfirmDialog**: Confirmation dialog component
  - Purpose: Confirm destructive actions (delete, cleanup)
  - Responsibilities: Action confirmation, cancel handling
  - Why separate: Reusable confirmation pattern

### Data Model Changes
No database schema changes required. Frontend uses existing API contracts:
- Camera API: `/api/v1/cameras` (GET, POST, PATCH, DELETE)
- Output Config API: `/api/v1/output-config` (GET, PATCH)
- Jobs API: `/api/v1/jobs` (future, will be added in backend)

### State/Workflow Design

#### Settings State Machine
```
States:
- viewing_list: Viewing cameras/output/notifications list
- creating: Creating new camera/config
- editing: Editing existing camera/config
- deleting: Confirming deletion
- saving: Submitting to API
- error: API error state

Transitions:
- viewing_list -> creating (Add button click)
- viewing_list -> editing (Edit button click)
- viewing_list -> deleting (Delete button click)
- creating/editing -> saving (Form submit)
- saving -> viewing_list (Success)
- saving -> error (API error)
- error -> editing (Retry)
- deleting -> viewing_list (Confirm/Cancel)
```

#### Camera Operation State Machine
```
States:
- idle: No operation running
- previewing: Live preview active
- capturing: Still capture in progress
- recording: Recording in progress
- timelapse_running: Timelapse active
- paused: Timelapse paused (interruption)
- error: Operation error

Transitions:
- idle -> previewing (Preview start)
- previewing -> capturing (Capture button)
- previewing -> recording (Record start)
- previewing -> timelapse_running (Timelapse start)
- recording -> previewing (Record stop)
- timelapse_running -> paused (User pause/interruption)
- timelapse_running -> idle (Complete/Stop)
- paused -> timelapse_running (Resume)
- paused -> idle (Cleanup)
- any -> error (API/hardware error)
- error -> idle (Clear error)
```

#### Job Status States
```
States from backend:
- pending: Job queued
- running: Job executing
- completed: Job finished successfully
- failed: Job failed

UI handles:
- Progress updates via WebSocket
- Job completion notifications
- Failed job error display
```

## Implementation Plan

### Phase 1: Foundation - Shared Components and Routing

**Goal**: Create reusable UI components and establish routing structure for settings and camera pages.

**Tasks**:

1. **Task 1.1: Create shared UI components**
   - **Architecture**: Build reusable component library
     - FormField: Label + input + error wrapper
     - Modal: Overlay with portal, focus trap using React hooks
     - Toast: Context provider + hook + ToastContainer component
     - ConfirmDialog: Modal specialization for confirmations
     - DiskSpaceWarning: Banner component with severity levels
   - **Considerations**:
     - Single Responsibility: Each component has one clear purpose
     - Dependency Inversion: Components accept props/callbacks, no direct API calls
     - DRY: Extract common patterns (modal backdrop, focus management)
     - Accessibility: ARIA labels, keyboard navigation, focus trapping
   - **Dependencies**: React, ReactDOM.createPortal
   - **Testing**: Unit tests for each component with user interactions

2. **Task 1.2: Implement Toast notification system**
   - **Architecture**: Context-based global notification system
     - ToastContext: Manages toast queue state
     - useToast hook: Provides `showToast(message, type)` function
     - ToastContainer: Renders toast stack at app root
     - Auto-dismiss after 5 seconds, manual dismiss option
   - **Considerations**:
     - Keep cyclomatic complexity low: Simple queue management
     - Performance: Limit max 5 toasts, auto-remove oldest
     - Accessibility: Announce toasts to screen readers (aria-live)
   - **Dependencies**: Task 1.1 (Toast component)
   - **Testing**: Test toast queue behavior, auto-dismiss timing

3. **Task 1.3: Update routing in App.tsx**
   - **Architecture**: Add routes for settings and camera pages
     - `/system` - SystemPage with nested settings routes
     - `/camera/:cameraId` - CameraPage with nested tab routes
     - `/camera/:cameraId/capture` - Default tab
     - `/camera/:cameraId/record` - Recording tab
     - `/camera/:cameraId/timelapse` - Timelapse tab
   - **Considerations**:
     - Open/Closed: Route configuration easily extensible
     - Type safety: Use typed route params from react-router-dom
     - Guard routes: Validate cameraId exists before rendering
   - **Dependencies**: react-router-dom v6+
   - **Testing**: Route navigation tests, 404 handling

4. **Task 1.4: Enhance Layout with dynamic camera navigation**
   - **Architecture**: Extend Layout.tsx to include camera tabs
     - Fetch cameras list using TanStack Query
     - Render dynamic links for each camera
     - Highlight active camera in navigation
     - Mobile: Hamburger menu for navigation collapse
   - **Considerations**:
     - Performance: Cache cameras query, refetch on focus
     - Responsive: CSS media queries for mobile layout
     - Accessibility: Proper nav landmark, skip links
   - **Dependencies**: Existing cameras API query
   - **Testing**: Test dynamic nav updates when cameras change

**Deliverables**:
- `frontend/src/components/common/FormField.tsx`
- `frontend/src/components/common/Modal.tsx`
- `frontend/src/components/common/Toast.tsx`
- `frontend/src/components/common/ConfirmDialog.tsx`
- `frontend/src/components/common/DiskSpaceWarning.tsx`
- `frontend/src/contexts/ToastContext.tsx`
- `frontend/src/hooks/useToast.ts`
- Updated `frontend/src/App.tsx` with new routes
- Updated `frontend/src/components/Layout.tsx` with dynamic nav

**Acceptance Criteria**:
- All shared components render correctly and are accessible
- Toast notifications appear and auto-dismiss
- Routing works for `/system` and `/camera/:cameraId`
- Camera navigation dynamically updates when cameras added/removed
- Mobile hamburger menu collapses/expands correctly

---

### Phase 2: System Settings - Cameras and Output Panels

**Goal**: Implement System Settings page with Cameras CRUD panel and Output configuration panel.

**Tasks**:

1. **Task 2.1: Create SystemPage layout with sidebar navigation**
   - **Architecture**: Two-column layout with sidebar + content area
     - SettingsSidebar: Fixed left column (200px) with nav links
     - Settings content: Flexible right column for active panel
     - Mobile: Sidebar collapses to top tabs
   - **Considerations**:
     - Responsive: CSS Grid for layout, mobile-first approach
     - State management: Use React Router to track active section
     - Accessibility: Proper landmark roles, focus management
   - **Dependencies**: React Router nested routes
   - **Testing**: Test sidebar navigation, mobile layout

2. **Task 2.2: Build CamerasPanel with camera list display**
   - **Architecture**: Camera list + Add/Edit/Delete actions
     - Display: Table or card grid showing camera name, type, status
     - Fetch cameras using TanStack Query (same query as HomePage)
     - Add button opens modal with CameraForm
     - Edit/Delete buttons inline on each camera row
   - **Considerations**:
     - DRY: Reuse camera query from HomePage (shared queryKey)
     - Optimistic updates: Update cache before API response
     - Error handling: Show error state, retry mechanism
     - Empty state: Helpful message when no cameras
   - **Dependencies**: apiClient, TanStack Query, Modal component
   - **Testing**: Test camera list rendering, loading/error states

3. **Task 2.3: Implement CameraForm for add/edit operations**
   - **Architecture**: Form component for camera creation/editing
     - Fields: name, device_path, camera_type (CSI/USB), enabled checkbox
     - Validation: Required fields, device_path format validation
     - Submit: POST /cameras (create) or PATCH /cameras/:id (update)
     - On success: Close modal, refetch cameras, show toast
   - **Considerations**:
     - Single Responsibility: Form only handles input, parent handles API
     - Validation: Client-side validation before submit
     - Cyclomatic complexity: Keep validation logic simple (<10)
     - Type safety: Use generated API types for request/response
   - **Dependencies**: FormField, apiClient, useToast
   - **Testing**: Test form validation, submit handling, error display

4. **Task 2.4: Implement camera delete with confirmation**
   - **Architecture**: Delete flow with ConfirmDialog
     - Delete button triggers ConfirmDialog
     - Confirm: DELETE /cameras/:id
     - Success: Refetch cameras, show success toast
     - Error: Show error toast, keep dialog open for retry
   - **Considerations**:
     - Safety: Confirmation prevents accidental deletion
     - Error handling: Clear error messages with retry option
     - Optimistic updates: Optional - remove from UI before API responds
   - **Dependencies**: ConfirmDialog, apiClient, useToast
   - **Testing**: Test confirmation flow, cancel vs confirm, API errors

5. **Task 2.5: Build OutputPanel for storage configuration**
   - **Architecture**: Form for output configuration
     - Fetch config: GET /output-config
     - Fields: recording_base_path, still_base_path, timelapse_base_path, retention_days, max_storage_gb
     - Display current disk usage under path fields
     - Submit: PATCH /output-config
   - **Considerations**:
     - Validation: Path format validation, numeric ranges
     - Disk info: Fetch disk stats from system stats API
     - Performance: Debounce path input to avoid excessive validation
     - Feedback: Success toast on save, error toast on failure
   - **Dependencies**: FormField, apiClient, useToast
   - **Testing**: Test form validation, save flow, disk info display

**Deliverables**:
- `frontend/src/pages/SystemPage.tsx` (enhanced layout)
- `frontend/src/components/settings/SettingsSidebar.tsx`
- `frontend/src/components/settings/CamerasPanel.tsx`
- `frontend/src/components/settings/CameraForm.tsx`
- `frontend/src/components/settings/OutputPanel.tsx`
- CSS files for settings layout and panels

**Acceptance Criteria**:
- System Settings page displays with sidebar navigation
- Cameras can be added, edited, and deleted via UI
- Camera list updates in real-time after CRUD operations
- Output configuration form saves successfully
- Disk space information displays correctly
- All forms validate input before submission
- Success/error toasts appear for all operations

---

### Phase 3: System Settings - Notifications and Temperature Panels

**Goal**: Complete System Settings page with Notifications preferences and Temperature stub panel.

**Tasks**:

1. **Task 3.1: Implement NotificationsPanel for browser notification preferences**
   - **Architecture**: Preferences form for notification settings
     - Permission request button (if not granted)
     - Checkboxes: Enable recording completion, timelapse completion, error notifications
     - Settings stored in localStorage (no backend API yet)
     - Test notification button to verify permissions
   - **Considerations**:
     - Browser API: Use Notification API, check permission status
     - Graceful degradation: Handle browsers without notification support
     - User control: Clear enable/disable options per event type
     - Privacy: Explain what notifications will be sent
   - **Dependencies**: Browser Notification API, localStorage
   - **Testing**: Test permission request flow, preference persistence

2. **Task 3.2: Create notification service for browser notifications**
   - **Architecture**: Service module for triggering notifications
     - `showNotification(title, body, options)`: Wrapper for Notification API
     - Check permission before showing notification
     - Integrate with WebSocket job_update events
     - Fire notifications on recording/timelapse completion
   - **Considerations**:
     - Single Responsibility: Service only handles notification display
     - Error handling: Gracefully handle permission denied
     - User preferences: Check localStorage before showing notification
     - Lifecycle: Request permission once, store result
   - **Dependencies**: NotificationsPanel preferences
   - **Testing**: Test notification trigger logic, permission handling

3. **Task 3.3: Integrate notification service with WebSocket events**
   - **Architecture**: Connect job completion events to notifications
     - Subscribe to `job_update` WebSocket messages
     - On `status: completed` or `status: failed`, show notification
     - Include job type (recording/timelapse) and camera name in message
   - **Considerations**:
     - Performance: Only trigger if user has notifications enabled
     - Message clarity: Clear, actionable notification text
     - Deduplication: Avoid duplicate notifications for same job
   - **Dependencies**: WebSocket client, notification service
   - **Testing**: Test notification triggers on job events

4. **Task 3.4: Build TemperaturePanel placeholder**
   - **Architecture**: Simple stub UI for future temperature control
     - Display "Temperature Control Coming Soon" message
     - Show mock UI elements (disabled controls) for visual design
     - Prepare component structure for future GPIO integration
   - **Considerations**:
     - Open/Closed: Design interface ready for future implementation
     - Visual clarity: Make it clear feature is not yet active
     - No API calls: Completely frontend stub
   - **Dependencies**: None
   - **Testing**: Basic rendering test

**Deliverables**:
- `frontend/src/components/settings/NotificationsPanel.tsx`
- `frontend/src/components/settings/TemperaturePanel.tsx`
- `frontend/src/services/notifications.ts`
- Integration of notification service with WebSocket handlers

**Acceptance Criteria**:
- NotificationsPanel requests and displays permission status
- User can enable/disable notification types
- Browser notifications trigger on recording/timelapse completion
- Test notification button works correctly
- TemperaturePanel displays placeholder UI
- Notification preferences persist across sessions

---

### Phase 4: Camera Tabs - Live Preview and Capture

**Goal**: Implement CameraPage with live preview and capture functionality.

**Tasks**:

1. **Task 4.1: Create CameraPage layout and routing**
   - **Architecture**: Container for per-camera view
     - URL param: `/camera/:cameraId`
     - Fetch camera details: GET /cameras/:cameraId
     - Display camera name, type, status in header
     - Render LivePreview component (always visible)
     - Render CameraTabNav and route to Capture/Record/Timelapse tabs
   - **Considerations**:
     - Error handling: 404 if camera not found
     - Loading state: Skeleton loader while fetching camera
     - Performance: Cache camera data, refetch on window focus
     - Navigation: Default to /capture tab
   - **Dependencies**: apiClient, TanStack Query, react-router-dom
   - **Testing**: Test camera loading, 404 handling, tab navigation

2. **Task 4.2: Build LivePreview component for MJPEG streaming**
   - **Architecture**: Image element displaying MJPEG stream
     - Stream URL: `/api/v1/cameras/:cameraId/stream` (backend endpoint)
     - Use <img src={streamUrl} /> for MJPEG display
     - Error handling: Show placeholder on stream error
     - Reconnection: Retry stream on error with exponential backoff
     - Loading state: Show spinner while stream connects
   - **Considerations**:
     - Performance: Only load stream when component mounted
     - Cleanup: Stop stream on unmount to free encoder
     - Error recovery: Auto-retry with backoff (1s, 2s, 4s, max 10s)
     - Memory: Ensure img element cleaned up properly
   - **Dependencies**: Camera ID from route params
   - **Testing**: Test stream loading, error handling, reconnection

3. **Task 4.3: Implement CameraTabNav for tab navigation**
   - **Architecture**: Tabbed navigation component
     - Tabs: Capture, Record, Timelapse
     - Active tab highlighted based on current route
     - Click tab navigates to `/camera/:cameraId/:tab`
     - Disable tabs if camera offline/disabled
   - **Considerations**:
     - Accessibility: ARIA roles for tabs, keyboard navigation
     - Visual feedback: Clear active tab indication
     - Responsive: Stacked tabs on mobile if needed
   - **Dependencies**: react-router-dom
   - **Testing**: Test tab navigation, active tab highlighting

4. **Task 4.4: Build CaptureTab with still image capture**
   - **Architecture**: Capture controls and image display
     - Quality selector: Dropdown for JPEG quality (low/medium/high/max)
     - Format selector: JPEG/PNG (if supported by camera)
     - Capture button: POST /cameras/:cameraId/capture
     - Display captured image thumbnail with download link
     - Show recent captures list (last 5)
   - **Considerations**:
     - API integration: Handle capture response (image URL or base64)
     - File download: Trigger browser download on image click
     - Validation: Check camera is online before allowing capture
     - Feedback: Show capturing state, success/error toast
   - **Dependencies**: apiClient, useToast
   - **Testing**: Test capture flow, quality selection, download

5. **Task 4.5: Add JobStatusDisplay component**
   - **Architecture**: Display current/past jobs for camera
     - Fetch jobs: GET /jobs?camera_id=:cameraId (future API)
     - Display job list: Type, status, progress, start/end time
     - Subscribe to job_update WebSocket for real-time progress
     - Progress bar for running jobs
   - **Considerations**:
     - Real-time updates: WebSocket integration for job progress
     - Filtering: Show only jobs for current camera
     - Performance: Limit to last 10 jobs, paginate if needed
     - Accessibility: Progress bar with aria-valuenow
   - **Dependencies**: Jobs API (future), WebSocket client
   - **Testing**: Test job list display, WebSocket updates

**Deliverables**:
- `frontend/src/pages/CameraPage.tsx`
- `frontend/src/components/camera/CameraTabNav.tsx`
- `frontend/src/components/camera/LivePreview.tsx`
- `frontend/src/components/camera/CaptureTab.tsx`
- `frontend/src/components/camera/JobStatusDisplay.tsx`
- CSS files for camera page layout and components

**Acceptance Criteria**:
- CameraPage loads camera details correctly
- Live preview displays MJPEG stream with <500ms latency
- Preview auto-reconnects on stream error
- Capture tab allows still image capture with quality selection
- Captured images can be downloaded
- Job status displays current operations
- Tab navigation works correctly

---

### Phase 5: Camera Tabs - Recording with Disk Space Warnings

**Goal**: Implement RecordTab with recording controls and disk space warning system.

**Tasks**:

1. **Task 5.1: Build RecordTab with recording controls**
   - **Architecture**: Recording start/stop controls
     - Bitrate selector: Dropdown (1Mbps, 2Mbps, 4Mbps, 8Mbps)
     - Resolution selector: Based on camera capabilities
     - FPS selector: 15, 24, 30, 60 fps
     - Record button: POST /cameras/:cameraId/record/start
     - Stop button: POST /cameras/:cameraId/record/stop
     - Recording indicator: Pulsing red dot when recording active
     - Duration display: Live timer showing recording duration
   - **Considerations**:
     - State management: Track recording state (idle/recording)
     - Encoder constraint: Only one H.264 recording at a time
     - API errors: Handle encoder busy error (409 Conflict)
     - Validation: Check camera online and disk space before start
   - **Dependencies**: apiClient, useToast, DiskSpaceWarning
   - **Testing**: Test record start/stop, encoder busy handling

2. **Task 5.2: Integrate DiskSpaceWarning in RecordTab**
   - **Architecture**: Warning banner above recording controls
     - Fetch disk stats from system stats API
     - Display warning if disk free < 1GB (yellow) or < 500MB (red)
     - Block record start if disk free < 500MB (critical threshold)
     - Real-time updates via WebSocket stats_update
   - **Considerations**:
     - Safety: Prevent recording when disk full
     - Clarity: Clear messaging about why recording blocked
     - Real-time: Update disk status via WebSocket, not just on load
     - Threshold logic: Warning at 1GB, critical block at 500MB
   - **Dependencies**: DiskSpaceWarning component, WebSocket stats
   - **Testing**: Test warning display at thresholds, record blocking

3. **Task 5.3: Add recording duration timer**
   - **Architecture**: Live timer displaying recording duration
     - Start timer when recording starts
     - Update every second using setInterval
     - Format: HH:MM:SS
     - Stop and reset when recording stops
   - **Considerations**:
     - Performance: Use useEffect cleanup to clear interval
     - Accuracy: Timer may drift, consider using timestamps
     - Lifecycle: Reset timer if component unmounts during recording
   - **Dependencies**: React hooks (useEffect, useState)
   - **Testing**: Test timer start/stop, format display

4. **Task 5.4: Handle encoder busy conflicts**
   - **Architecture**: Error handling for concurrent recordings
     - Detect 409 Conflict response from record start API
     - Show error toast: "H.264 encoder busy. Only one recording allowed."
     - Optionally: Show which camera is currently recording
   - **Considerations**:
     - User clarity: Explain encoder limitation clearly
     - Helpful info: Tell user which camera has encoder
     - Recovery: Allow retry after other recording stops
   - **Dependencies**: API error handling, useToast
   - **Testing**: Test 409 error display, error message clarity

5. **Task 5.5: Display recorded videos list**
   - **Architecture**: List of recent recordings for camera
     - Fetch recordings: GET /files/recordings?camera_id=:cameraId
     - Display: Filename, duration, size, timestamp
     - Actions: Play (video player modal), Download, Delete
     - Pagination: Show last 10, load more button
   - **Considerations**:
     - File serving: Secure file serving via backend API
     - Video playback: Use HTML5 <video> element in modal
     - Storage info: Display total storage used by recordings
     - Delete confirmation: Use ConfirmDialog for deletion
   - **Dependencies**: Files API, Modal, ConfirmDialog
   - **Testing**: Test recordings list, playback, delete

**Deliverables**:
- `frontend/src/components/camera/RecordTab.tsx`
- Integration of DiskSpaceWarning in RecordTab
- Recording duration timer implementation
- Encoder busy error handling
- Recorded videos list display

**Acceptance Criteria**:
- Recording can be started/stopped with bitrate selection
- Disk space warning appears when free space < 1GB
- Recording blocked when disk space < 500MB
- Recording duration timer displays correctly
- Encoder busy (409) errors handled gracefully
- Recent recordings list displays and allows playback/download
- Only one H.264 recording allowed at a time

---

### Phase 6: Camera Tabs - Timelapse with Resume and Cleanup

**Goal**: Implement TimelapseTab with timelapse scheduling, interruption recovery, and cleanup UI.

**Tasks**:

1. **Task 6.1: Build TimelapseTab with timelapse controls**
   - **Architecture**: Timelapse configuration and control
     - Interval selector: Input for interval in seconds (default 60s)
     - Duration selector: Optional max duration or frame count
     - Quality selector: JPEG quality for frames
     - Start button: POST /cameras/:cameraId/timelapse/start
     - Pause button: POST /cameras/:cameraId/timelapse/pause
     - Stop button: POST /cameras/:cameraId/timelapse/stop
     - Status display: Show frames captured, estimated completion
   - **Considerations**:
     - Validation: Minimum interval (5s), reasonable max duration
     - State display: Show timelapse active/paused/stopped state
     - Disk space check: Warn if insufficient space for estimated frames
     - Job integration: Create job record when starting timelapse
   - **Dependencies**: apiClient, useToast, DiskSpaceWarning
   - **Testing**: Test timelapse start/pause/stop, validation

2. **Task 6.2: Implement timelapse interruption detection**
   - **Architecture**: Detect and display interrupted timelapses
     - On CameraPage mount, check for paused timelapses (via job status)
     - If paused timelapse exists, show resume banner
     - Banner: "Interrupted timelapse detected. Resume or cleanup?"
     - Resume button: POST /cameras/:cameraId/timelapse/resume
     - Cleanup button: Opens cleanup confirmation dialog
   - **Considerations**:
     - Persistence: Timelapse state persisted in backend database
     - User choice: Clear options to resume or discard
     - Safety: Confirmation before cleanup (data loss)
   - **Dependencies**: Jobs API, ConfirmDialog
   - **Testing**: Test interruption detection, resume flow

3. **Task 6.3: Build timelapse cleanup UI**
   - **Architecture**: Cleanup confirmation and execution
     - Detect interrupted timelapses with partial frames
     - Cleanup dialog shows: Frames captured, disk space used
     - Options: "Keep frames and generate video" or "Delete all frames"
     - Generate video: POST /cameras/:cameraId/timelapse/finalize
     - Delete frames: DELETE /cameras/:cameraId/timelapse/:jobId
   - **Considerations**:
     - User information: Show what will be deleted/kept
     - Safety: Clear confirmation, explain data loss
     - Feedback: Progress indication if generating video
     - Job tracking: Create job for video generation
   - **Dependencies**: ConfirmDialog, Jobs API, useToast
   - **Testing**: Test cleanup options, video generation, deletion

4. **Task 6.4: Display timelapse progress and preview**
   - **Architecture**: Real-time timelapse progress display
     - Show frames captured counter
     - Show estimated remaining time (if duration set)
     - Preview: Display last captured frame thumbnail
     - Progress bar: Visual progress toward completion
   - **Considerations**:
     - Real-time updates: WebSocket job_update for frame count
     - Preview: Fetch last frame periodically (every 10s)
     - Performance: Lazy load preview, don't block UI
     - Accessibility: Progress bar with aria-valuenow
   - **Dependencies**: WebSocket client, Jobs API
   - **Testing**: Test progress updates, preview display

5. **Task 6.5: Display completed timelapse videos list**
   - **Architecture**: List of generated timelapse videos
     - Fetch videos: GET /files/timelapses?camera_id=:cameraId
     - Display: Filename, frame count, duration, size, timestamp
     - Actions: Play (video player modal), Download, Delete
     - Pagination: Last 10 videos, load more
   - **Considerations**:
     - Video playback: HTML5 <video> in modal
     - Storage: Show total timelapse storage used
     - Delete: Confirmation dialog before deletion
   - **Dependencies**: Files API, Modal, ConfirmDialog
   - **Testing**: Test timelapse list, playback, deletion

**Deliverables**:
- `frontend/src/components/camera/TimelapseTab.tsx`
- `frontend/src/components/camera/TimelapseResumeBar.tsx`
- `frontend/src/components/camera/TimelapseCleanupDialog.tsx`
- Timelapse progress and preview display
- Completed timelapse videos list

**Acceptance Criteria**:
- Timelapse can be started with interval/duration configuration
- Timelapse can be paused and resumed
- Interrupted timelapses detected on page load
- Cleanup dialog offers keep or delete options
- Progress updates in real-time via WebSocket
- Last captured frame preview displays during timelapse
- Completed timelapse videos list with playback/download
- Disk space warnings appear before starting timelapse

---

### Phase 7: Integration and Polish

**Goal**: Integrate all components, add final polish, and ensure end-to-end functionality.

**Tasks**:

1. **Task 7.1: Integrate job system across all tabs**
   - **Architecture**: Centralized job tracking and display
     - JobStatusDisplay shows jobs from all tabs (capture, record, timelapse)
     - Job creation: All operations create job records
     - Job completion: Trigger notifications, update UI
     - Job errors: Display error messages, allow retry
   - **Considerations**:
     - Consistency: Same job display across all tabs
     - Real-time: WebSocket updates for all job types
     - Error recovery: Clear error messages, retry actions
   - **Dependencies**: All tabs, Jobs API, WebSocket
   - **Testing**: Test job creation from each tab, completion flow

2. **Task 7.2: Enhance HomePage quick actions with navigation**
   - **Architecture**: Link quick actions to camera operations
     - Capture Still: Navigate to first enabled camera /capture tab
     - Start Recording: Navigate to first enabled camera /record tab
     - Start Timelapse: Navigate to first enabled camera /timelapse tab
     - Settings: Navigate to /system
     - Disable actions if no cameras enabled
   - **Considerations**:
     - User experience: Quick access to common actions
     - Validation: Check cameras exist and are enabled
     - Feedback: Show message if no cameras available
   - **Dependencies**: Camera list query, react-router-dom
   - **Testing**: Test navigation, disabled state handling

3. **Task 7.3: Add mobile-responsive design**
   - **Architecture**: Mobile-first responsive layouts
     - Layout: Hamburger menu for navigation on mobile (<768px)
     - Settings: Sidebar converts to top tabs on mobile
     - Camera tabs: Stacked tabs on mobile, scrollable
     - Modals: Full-screen on mobile for better UX
     - Touch-friendly: Larger tap targets (min 44x44px)
   - **Considerations**:
     - Performance: CSS media queries, no JS breakpoint detection
     - Accessibility: Touch targets meet WCAG 2.1 AA (min 44x44px)
     - Testing: Test on mobile viewport sizes
   - **Dependencies**: CSS media queries
   - **Testing**: Test mobile layouts, hamburger menu

4. **Task 7.4: Implement loading and error states consistently**
   - **Architecture**: Consistent loading/error UI patterns
     - Loading: Skeleton loaders or spinners
     - Error: Error boundary for component crashes
     - Empty states: Helpful messages when no data
     - Network errors: Retry button, offline indicator
   - **Considerations**:
     - User clarity: Clear loading and error messages
     - Recovery: Always provide retry mechanism
     - Accessibility: Loading announced to screen readers
   - **Dependencies**: Error boundary component
   - **Testing**: Test loading states, error handling, retry

5. **Task 7.5: Add keyboard navigation and accessibility**
   - **Architecture**: Full keyboard navigation support
     - Tab navigation: Logical tab order
     - Shortcuts: Enter to submit forms, Escape to close modals
     - Focus management: Focus trap in modals, focus restore
     - ARIA labels: All interactive elements labeled
     - Screen reader: Meaningful announcements for state changes
   - **Considerations**:
     - WCAG 2.1 AA: Meet accessibility guidelines
     - Testing: Keyboard-only navigation testing
     - Focus visible: Clear focus indicators (CSS :focus-visible)
   - **Dependencies**: ARIA attributes, focus management hooks
   - **Testing**: Keyboard navigation tests, screen reader testing

6. **Task 7.6: Performance optimization**
   - **Architecture**: Optimize rendering and network
     - Code splitting: Lazy load camera pages, settings pages
     - Query optimization: Proper cache keys, stale times
     - WebSocket: Debounce rapid updates (stats every 2s, not more)
     - Image optimization: Lazy load thumbnails, responsive images
     - Bundle size: Analyze and optimize bundle size
   - **Considerations**:
     - Performance budget: <500KB gzipped frontend bundle
     - Lazy loading: Use React.lazy for route-based splitting
     - Memoization: React.memo for expensive components
   - **Dependencies**: Vite code splitting, React.lazy
   - **Testing**: Performance testing, bundle size analysis

**Deliverables**:
- Integration of job system across all components
- Enhanced HomePage quick actions
- Mobile-responsive CSS for all pages
- Consistent loading/error state handling
- Full keyboard navigation and accessibility support
- Performance optimizations (code splitting, lazy loading)

**Acceptance Criteria**:
- All operations create and update jobs correctly
- HomePage quick actions navigate to correct camera tabs
- Mobile layout works correctly on <768px viewports
- Hamburger menu functions on mobile
- All components have loading and error states
- Keyboard navigation works throughout the app
- Focus management correct in modals and dialogs
- WCAG 2.1 AA compliance verified
- Frontend bundle size <500KB gzipped
- No performance regressions (Lighthouse score >90)

---

## Design Principles Application

### SOLID Compliance

**Single Responsibility Principle**:
- Each component has one clear purpose:
  - CamerasPanel: Camera CRUD only
  - LivePreview: Stream display only
  - JobStatusDisplay: Job display only
- Services separated from UI:
  - notifications.ts: Browser notification logic
  - API calls via apiClient, not in components

**Open/Closed Principle**:
- Components accept props/callbacks for extension
- Settings panels easily added to SettingsSidebar
- New camera tabs can be added without modifying CameraTabNav
- Toast types extensible without modifying ToastContext

**Liskov Substitution Principle**:
- FormField component accepts any input element
- Modal component accepts any content
- Tab navigation works with any tab content

**Interface Segregation Principle**:
- Components receive only props they need
- No "god" props objects with unused properties
- Specialized components (CaptureTab, RecordTab) instead of monolithic CameraControls

**Dependency Inversion Principle**:
- Components depend on abstractions (apiClient, useToast hook)
- No direct fetch() calls in components
- WebSocket client injected, not hard-coded

### DRY Analysis

**Reusable Patterns**:
- FormField: Extract common form field layout (label, input, error)
- Modal: Reusable dialog wrapper for all modals/confirmations
- ConfirmDialog: Modal specialization for confirmations
- DiskSpaceWarning: Reusable warning banner across tabs
- JobStatusDisplay: Shared job display across all camera tabs

**Common Utilities**:
- useToast hook: Centralized toast notifications
- apiClient: Single HTTP client for all API calls
- wsClient: Single WebSocket client for all subscriptions
- formatDuration: Shared utility for time formatting
- formatBytes: Shared utility for file size formatting

### Complexity Management

**Cyclomatic Complexity Strategy**:
- Keep component render logic simple (<10 branches)
- Extract complex logic to hooks:
  - useCameraStatus: Camera status state management
  - useRecordingTimer: Recording duration timer
  - useTimelapseProgress: Timelapse progress tracking
- Form validation: Extract to validation functions
- API error handling: Centralized error handling utilities

**Cognitive Complexity Strategy**:
- Limit nesting: Max 3 levels in render methods
- Early returns: Exit early for loading/error states
- Component composition: Break large components into smaller parts
- Descriptive names: Clear variable and function names

**Function Size Guidelines**:
- Component functions: <100 lines
- Hook functions: <50 lines
- Utility functions: <30 lines
- Decompose large functions into smaller, focused functions

### System Constraints

**Resource Budget**:
- Frontend bundle: <500KB gzipped
- Memory: <50MB for React app (monitored via Chrome DevTools)
- API calls: Cached via TanStack Query, staleTime: 30s
- WebSocket: Single connection, reused across app

**Performance Requirements**:
- Initial load: <2s on LAN (measured with Lighthouse)
- UI interactions: <100ms response time
- Preview latency: <500ms end-to-end
- API response: <200ms for non-camera operations

**Security Considerations**:
- Input validation: All form inputs validated client-side
- XSS prevention: React escapes content by default
- CSRF: Use credentials: "include" for API calls
- File serving: Via backend API, no direct file access

**Scalability Strategy**:
- Component-based: Easy to add new camera tabs/settings panels
- Code splitting: Lazy load pages to reduce initial bundle
- Query caching: Reduce API load with TanStack Query
- WebSocket: Efficient real-time updates, single connection

---

## Integration Points

### Frontend ↔ Backend API

**Camera Operations**:
- GET /api/v1/cameras - List cameras
- POST /api/v1/cameras - Create camera
- GET /api/v1/cameras/:id - Get camera details
- PATCH /api/v1/cameras/:id - Update camera
- DELETE /api/v1/cameras/:id - Delete camera
- GET /api/v1/cameras/:id/stream - MJPEG preview stream
- POST /api/v1/cameras/:id/capture - Capture still image
- POST /api/v1/cameras/:id/record/start - Start recording
- POST /api/v1/cameras/:id/record/stop - Stop recording
- POST /api/v1/cameras/:id/timelapse/start - Start timelapse
- POST /api/v1/cameras/:id/timelapse/pause - Pause timelapse
- POST /api/v1/cameras/:id/timelapse/resume - Resume timelapse
- POST /api/v1/cameras/:id/timelapse/stop - Stop timelapse

**Configuration**:
- GET /api/v1/output-config - Get output configuration
- PATCH /api/v1/output-config - Update output configuration

**Jobs (Future API)**:
- GET /api/v1/jobs?camera_id=:id - List jobs for camera
- GET /api/v1/jobs/:id - Get job details
- DELETE /api/v1/jobs/:id - Delete job

**Files (Future API)**:
- GET /api/v1/files/recordings?camera_id=:id - List recordings
- GET /api/v1/files/timelapses?camera_id=:id - List timelapses
- GET /api/v1/files/:id - Download file
- DELETE /api/v1/files/:id - Delete file

### Frontend ↔ WebSocket

**Message Types Consumed**:
- stats_update: System statistics (CPU, memory, disk, temperature)
- camera_event: Camera status changes (online, offline, error)
- job_update: Job progress and status (recording, timelapse)

**Subscriptions**:
- Home Dashboard: stats_update, camera_event
- Camera Pages: camera_event (for specific camera), job_update (for camera jobs)
- Settings: camera_event (for camera list updates)

---

## Testing Strategy

### Unit Tests
**Components**:
- FormField: Test label, input, error rendering
- Modal: Test open/close, focus trap, escape key
- Toast: Test display, auto-dismiss, manual dismiss
- ConfirmDialog: Test confirm/cancel actions
- DiskSpaceWarning: Test threshold display, severity levels

**Hooks**:
- useToast: Test toast queue management
- useCameraStatus: Test status updates via WebSocket
- useRecordingTimer: Test timer start/stop/reset

**Services**:
- notifications.ts: Test permission requests, notification display

### Integration Tests
**Flows**:
- Camera CRUD: Add camera → appears in list → edit → delete
- Recording: Start recording → duration timer → stop → video in list
- Timelapse: Start timelapse → pause → resume → complete → video in list
- Settings: Update output config → save → reload → config persisted

### Component Tests (Vitest + Testing Library)
**Settings Panels**:
- CamerasPanel: Test camera list render, add/edit/delete flows
- OutputPanel: Test form validation, save flow
- NotificationsPanel: Test permission request, preference save

**Camera Tabs**:
- CaptureTab: Test capture button, quality selection
- RecordTab: Test record start/stop, disk warning display
- TimelapseTab: Test timelapse start/pause/resume, cleanup

### E2E Tests (Playwright)
**Critical User Journeys**:
1. Add new camera → navigate to camera page → capture still image
2. Start recording → wait 10s → stop recording → verify video exists
3. Start timelapse → pause → resume → stop → verify video generated
4. Update output configuration → verify persisted after reload
5. Enable notifications → trigger job completion → verify notification

---

## Risks and Mitigations

**Risk 1: MJPEG stream reliability**
- **Issue**: Stream may drop, browser may not handle MJPEG well
- **Mitigation**: Auto-reconnect logic with exponential backoff, fallback to polling image endpoint

**Risk 2: WebSocket connection stability**
- **Issue**: WebSocket may disconnect, causing missed updates
- **Mitigation**: Auto-reconnect with connection state display, fallback to polling for critical data

**Risk 3: Browser notification permission denied**
- **Issue**: User may deny notification permission
- **Mitigation**: Graceful degradation, in-app toast notifications as fallback

**Risk 4: Mobile UX challenges**
- **Issue**: Complex controls may be difficult on mobile
- **Mitigation**: Touch-friendly design (44px targets), simplified mobile layout, testing on real devices

**Risk 5: Form validation complexity**
- **Issue**: Complex validation rules may lead to bugs
- **Mitigation**: Use validation library (e.g., Zod), comprehensive unit tests for validation logic

**Risk 6: Job state synchronization**
- **Issue**: Job state may desync between UI and backend
- **Mitigation**: Single source of truth (backend), refetch jobs on WebSocket reconnect

**Risk 7: Large bundle size**
- **Issue**: Too many dependencies may bloat bundle
- **Mitigation**: Code splitting, lazy loading, bundle analysis (Vite rollup-plugin-visualizer)

**Risk 8: Accessibility gaps**
- **Issue**: May miss accessibility requirements
- **Mitigation**: Use axe DevTools, test with screen reader, keyboard-only navigation testing

---

## Dependencies and Prerequisites

### External Dependencies
- React 18+ (already installed)
- React Router DOM 6+ (already installed)
- TanStack Query 5+ (already installed)
- TypeScript 5+ (already installed)

### New Dependencies (if needed)
- None required - all features can be built with existing dependencies

### Backend API Prerequisites
- Camera CRUD endpoints (✅ complete)
- Output config endpoints (✅ complete)
- WebSocket stats broadcaster (✅ complete)
- Jobs API endpoints (⏳ pending - Phase 2/3)
- Files API endpoints (⏳ pending - Phase 2/4)

### Browser API Prerequisites
- Notification API (standard, widely supported)
- localStorage (standard, widely supported)

---

## Timeline Estimate

| Phase | Tasks | Estimated Time | Priority |
|-------|-------|----------------|----------|
| Phase 1: Foundation | 4 tasks | 2-3 days | CRITICAL |
| Phase 2: Settings - Cameras/Output | 5 tasks | 3-4 days | HIGH |
| Phase 3: Settings - Notifications/Temp | 4 tasks | 2 days | MEDIUM |
| Phase 4: Camera Tabs - Preview/Capture | 5 tasks | 3-4 days | HIGH |
| Phase 5: Camera Tabs - Recording | 5 tasks | 3-4 days | HIGH |
| Phase 6: Camera Tabs - Timelapse | 5 tasks | 3-4 days | HIGH |
| Phase 7: Integration & Polish | 6 tasks | 3-4 days | HIGH |

**Total Estimated Time**: 19-27 days

**Parallel Work Opportunities**:
- Phase 2 and Phase 4 can be worked in parallel (Settings vs Camera Tabs)
- Phase 3 can overlap with Phase 5 (lower priority features)

**Recommended Implementation Order** (accounting for dependencies):
1. Phase 1 (Foundation) - Required first
2. Phase 2 (Settings Cameras/Output) - High value, no dependencies
3. Phase 4 (Camera Tabs Preview/Capture) - Can start while Phase 3 ongoing
4. Phase 3 (Settings Notifications/Temp) - Lower priority, can overlap
5. Phase 5 (Camera Tabs Recording) - Depends on Phase 4
6. Phase 6 (Camera Tabs Timelapse) - Depends on Phase 4
7. Phase 7 (Integration & Polish) - Final phase

**Optimized Timeline**: 15-20 days with parallel work

---

## Component Hierarchy Diagram

```
App
├── ToastContext.Provider
│   └── AuthProvider
│       └── QueryClientProvider
│           └── BrowserRouter
│               └── Routes
│                   ├── Layout
│                   │   ├── Header (with dynamic camera nav)
│                   │   ├── Main (Outlet)
│                   │   │   ├── HomePage
│                   │   │   │   ├── SystemStats
│                   │   │   │   ├── CameraStatusCard (per camera)
│                   │   │   │   └── QuickActions
│                   │   │   ├── SystemPage
│                   │   │   │   ├── SettingsSidebar
│                   │   │   │   └── (Outlet for settings panels)
│                   │   │   │       ├── CamerasPanel
│                   │   │   │       │   ├── CameraForm (in Modal)
│                   │   │   │       │   └── ConfirmDialog (for delete)
│                   │   │   │       ├── OutputPanel
│                   │   │   │       │   └── FormField (multiple)
│                   │   │   │       ├── NotificationsPanel
│                   │   │   │       │   └── FormField (checkboxes)
│                   │   │   │       └── TemperaturePanel
│                   │   │   └── CameraPage
│                   │   │       ├── LivePreview
│                   │   │       ├── CameraTabNav
│                   │   │       ├── JobStatusDisplay
│                   │   │       └── (Outlet for camera tabs)
│                   │   │           ├── CaptureTab
│                   │   │           ├── RecordTab
│                   │   │           │   └── DiskSpaceWarning
│                   │   │           └── TimelapseTab
│                   │   │               ├── TimelapseResumeBar
│                   │   │               ├── TimelapseCleanupDialog
│                   │   │               └── DiskSpaceWarning
│                   │   └── Footer
│                   └── LoginModal
└── ToastContainer (portal)
    └── Toast (per notification)
```

---

## File Structure

```
frontend/src/
├── components/
│   ├── common/
│   │   ├── FormField.tsx
│   │   ├── FormField.css
│   │   ├── Modal.tsx
│   │   ├── Modal.css
│   │   ├── Toast.tsx
│   │   ├── Toast.css
│   │   ├── ConfirmDialog.tsx
│   │   ├── ConfirmDialog.css
│   │   ├── DiskSpaceWarning.tsx
│   │   └── DiskSpaceWarning.css
│   ├── settings/
│   │   ├── SettingsSidebar.tsx
│   │   ├── SettingsSidebar.css
│   │   ├── CamerasPanel.tsx
│   │   ├── CamerasPanel.css
│   │   ├── CameraForm.tsx
│   │   ├── CameraForm.css
│   │   ├── OutputPanel.tsx
│   │   ├── OutputPanel.css
│   │   ├── NotificationsPanel.tsx
│   │   ├── NotificationsPanel.css
│   │   ├── TemperaturePanel.tsx
│   │   └── TemperaturePanel.css
│   ├── camera/
│   │   ├── CameraTabNav.tsx
│   │   ├── CameraTabNav.css
│   │   ├── LivePreview.tsx
│   │   ├── LivePreview.css
│   │   ├── CaptureTab.tsx
│   │   ├── CaptureTab.css
│   │   ├── RecordTab.tsx
│   │   ├── RecordTab.css
│   │   ├── TimelapseTab.tsx
│   │   ├── TimelapseTab.css
│   │   ├── TimelapseResumeBar.tsx
│   │   ├── TimelapseCleanupDialog.tsx
│   │   ├── JobStatusDisplay.tsx
│   │   └── JobStatusDisplay.css
│   ├── Layout.tsx (enhanced)
│   ├── Layout.css (enhanced)
│   └── ... (existing components)
├── contexts/
│   ├── ToastContext.tsx
│   └── ... (existing contexts)
├── hooks/
│   ├── useToast.ts
│   ├── useCameraStatus.ts
│   ├── useRecordingTimer.ts
│   └── useTimelapseProgress.ts
├── services/
│   └── notifications.ts
├── pages/
│   ├── SystemPage.tsx (enhanced)
│   ├── SystemPage.css
│   ├── CameraPage.tsx (new)
│   ├── CameraPage.css
│   └── ... (existing pages)
├── utils/
│   ├── formatDuration.ts
│   └── formatBytes.ts
└── App.tsx (enhanced routing)
```

---

## Status

**Status**: `.ready.md` - Plan complete and ready for implementation

**Next Steps**:
1. Review plan with team/stakeholder
2. Rename to `ui-remaining-components.in_progress.md` when starting implementation
3. Begin with Phase 1 (Foundation)
4. Implement phases sequentially or in parallel where possible
5. Move to `.claude/plans/completed/ui-remaining-components.md` when all phases complete

**Key Architectural Decisions**:
- React Router nested routes for settings panels and camera tabs
- Context-based toast notification system for global notifications
- WebSocket integration for real-time job progress and camera status
- Component-based architecture with clear separation of concerns
- Reusable shared components (Modal, FormField, DiskSpaceWarning)
- Browser Notification API for job completion alerts

**Estimated Complexity**: **High**
- Rationale: Multiple complex features (MJPEG streaming, job tracking, timelapse management), real-time updates, mobile responsiveness, accessibility requirements
- Phase 1-3: Medium complexity (forms, navigation, basic controls)
- Phase 4-6: High complexity (streaming, state machines, WebSocket integration)
- Phase 7: Medium complexity (polish, optimization)

**Critical Risks Identified**:
- MJPEG stream reliability (mitigation: auto-reconnect)
- WebSocket stability (mitigation: auto-reconnect, fallback polling)
- Mobile UX complexity (mitigation: touch-friendly design, testing)
- Job state synchronization (mitigation: backend as source of truth)

**Success Metrics**:
- All CRUD operations functional and tested
- Live preview <500ms latency
- Real-time updates via WebSocket working
- Mobile-responsive design on <768px viewports
- WCAG 2.1 AA accessibility compliance
- Frontend bundle <500KB gzipped
- All E2E tests passing for critical flows
