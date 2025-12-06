# Camera Tabs - Plan

## Overview

Implement dynamic per-camera tabs with live preview and capture/record/timelapse controls.

**Dependencies**: 05-frontend-foundation, 03-camera-system
**Estimated Duration**: 2-3 days

---

## Phase 1: Dynamic Navigation

### Goal
Generate navigation items from camera list.

### Tasks

1. **Update Navigation component to include cameras**
   - Query cameras from API
   - Add tab per enabled camera
   - Show status indicator (recording = red dot)
   - Handle camera deletion (redirect if viewing deleted)

### Acceptance Criteria
- [ ] Camera tabs appear in nav
- [ ] Status indicators work
- [ ] Deleted cameras handled

---

## Phase 2: Camera View Layout

### Goal
Split view with preview and controls.

### Desktop Layout
```
+------------------------------------------+
| Camera Name                    [⛶ Full]  |
+------------------------+-----------------+
|                        | [Capture|Record |
|   Live Preview         |  |Timelapse]   |
|                        |                 |
|   [MJPEG Stream]       | [Control Panel] |
|                        |                 |
|                        |                 |
+------------------------+-----------------+
```

### Mobile Layout
```
+------------------+
| Camera Name      |
+------------------+
| Live Preview     |
|                  |
+------------------+
| [Cap|Rec|TL]     |
+------------------+
| Control Panel    |
|                  |
+------------------+
```

### Tasks

1. **Create `src/pages/Camera/[id].tsx`**
   ```typescript
   import { useParams, Navigate } from 'react-router-dom';
   import { useCamera } from '@/api/hooks/useCameras';
   import { LivePreview } from './LivePreview';
   import { CameraControls } from './CameraControls';
   import styles from './CameraView.module.css';

   export default function CameraView() {
     const { id } = useParams<{ id: string }>();
     const cameraId = parseInt(id || '0', 10);
     const { data: camera, isLoading, isError } = useCamera(cameraId);

     if (isLoading) return <div>Loading...</div>;
     if (isError || !camera) return <Navigate to="/" replace />;

     return (
       <div className={styles.view}>
         <header className={styles.header}>
           <h1>{camera.name}</h1>
           <button className={styles.fullscreen}>⛶</button>
         </header>

         <div className={styles.content}>
           <div className={styles.preview}>
             <LivePreview cameraId={cameraId} />
           </div>
           <div className={styles.controls}>
             <CameraControls cameraId={cameraId} />
           </div>
         </div>
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] 60/40 split on desktop
- [ ] Stacked on mobile
- [ ] Fullscreen button works

---

## Phase 3: Live Preview Component

### Goal
Display MJPEG stream with error handling.

### States
1. **Loading**: Spinner
2. **Streaming**: MJPEG image
3. **Error**: "Camera Offline" message
4. **Reconnecting**: "Reconnecting..." with retry

### Tasks

1. **Create `src/pages/Camera/LivePreview.tsx`**
   ```typescript
   import { useState, useEffect, useRef } from 'react';
   import { Card } from '@/components/common/Card';
   import styles from './LivePreview.module.css';

   interface LivePreviewProps {
     cameraId: number;
   }

   type StreamState = 'loading' | 'streaming' | 'error' | 'reconnecting';

   export function LivePreview({ cameraId }: LivePreviewProps) {
     const [state, setState] = useState<StreamState>('loading');
     const [retryCount, setRetryCount] = useState(0);
     const imgRef = useRef<HTMLImageElement>(null);
     const streamUrl = `/api/v1/cameras/${cameraId}/stream`;

     useEffect(() => {
       setState('loading');
       setRetryCount(0);
     }, [cameraId]);

     const handleLoad = () => {
       setState('streaming');
       setRetryCount(0);
     };

     const handleError = () => {
       if (retryCount < 5) {
         setState('reconnecting');
         setTimeout(() => {
           setRetryCount((c) => c + 1);
           // Force reload by updating src
           if (imgRef.current) {
             imgRef.current.src = `${streamUrl}?t=${Date.now()}`;
           }
         }, Math.min(1000 * Math.pow(2, retryCount), 16000));
       } else {
         setState('error');
       }
     };

     return (
       <Card className={styles.preview}>
         {state === 'loading' && (
           <div className={styles.overlay}>
             <div className={styles.spinner} />
             <span>Connecting...</span>
           </div>
         )}

         {state === 'reconnecting' && (
           <div className={styles.overlay}>
             <div className={styles.spinner} />
             <span>Reconnecting... (attempt {retryCount + 1})</span>
           </div>
         )}

         {state === 'error' && (
           <div className={styles.overlay}>
             <span className={styles.errorIcon}>📷</span>
             <span>Camera Offline</span>
             <button onClick={() => setRetryCount(0)}>Retry</button>
           </div>
         )}

         <img
           ref={imgRef}
           src={streamUrl}
           alt="Live Preview"
           className={styles.stream}
           onLoad={handleLoad}
           onError={handleError}
           style={{ display: state === 'streaming' ? 'block' : 'none' }}
         />

         <div className={styles.info}>
           {state === 'streaming' && <span className={styles.live}>● LIVE</span>}
         </div>
       </Card>
     );
   }
   ```

### Acceptance Criteria
- [ ] Stream displays correctly
- [ ] Error state shows message
- [ ] Reconnection with backoff
- [ ] LIVE indicator visible

---

## Phase 4: Control Tabs

### Goal
Tabbed interface for Capture, Record, Timelapse.

### Tasks

1. **Create `src/pages/Camera/CameraControls.tsx`**
   ```typescript
   import { useState } from 'react';
   import { Tabs } from '@/components/common/Tabs';
   import { CaptureTab } from './CaptureTab';
   import { RecordTab } from './RecordTab';
   import { TimelapseTab } from './TimelapseTab';
   import styles from './CameraControls.module.css';

   interface CameraControlsProps {
     cameraId: number;
   }

   const tabs = [
     { id: 'capture', label: 'Capture' },
     { id: 'record', label: 'Record' },
     { id: 'timelapse', label: 'Timelapse' },
   ];

   export function CameraControls({ cameraId }: CameraControlsProps) {
     const [activeTab, setActiveTab] = useState('capture');

     return (
       <div className={styles.controls}>
         <Tabs
           tabs={tabs}
           activeTab={activeTab}
           onTabChange={setActiveTab}
         />

         <div className={styles.panel}>
           {activeTab === 'capture' && <CaptureTab cameraId={cameraId} />}
           {activeTab === 'record' && <RecordTab cameraId={cameraId} />}
           {activeTab === 'timelapse' && <TimelapseTab cameraId={cameraId} />}
         </div>
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Tab switching works
- [ ] State persists per camera
- [ ] Smooth transitions

---

## Phase 5: Capture Tab

### Goal
Still image capture functionality.

### Tasks

1. **Create `src/pages/Camera/CaptureTab.tsx`**
   ```typescript
   import { useState } from 'react';
   import { useMutation } from '@tanstack/react-query';
   import { api } from '@/api/client';
   import { Button } from '@/components/common/Button';
   import { Card } from '@/components/common/Card';
   import styles from './CaptureTab.module.css';

   interface CaptureTabProps {
     cameraId: number;
   }

   interface CaptureResult {
     path: string;
     filename: string;
   }

   export function CaptureTab({ cameraId }: CaptureTabProps) {
     const [lastCapture, setLastCapture] = useState<CaptureResult | null>(null);
     const [quality, setQuality] = useState(85);

     const capture = useMutation({
       mutationFn: () =>
         api.post<CaptureResult>(`/api/v1/cameras/${cameraId}/capture`, {
           quality,
         }),
       onSuccess: (data) => {
         setLastCapture(data);
       },
     });

     return (
       <div className={styles.tab}>
         <Button
           size="lg"
           onClick={() => capture.mutate()}
           disabled={capture.isPending}
           className={styles.captureBtn}
         >
           {capture.isPending ? 'Capturing...' : '📷 Take Photo'}
         </Button>

         <div className={styles.settings}>
           <label>
             Quality: {quality}%
             <input
               type="range"
               min="1"
               max="100"
               value={quality}
               onChange={(e) => setQuality(Number(e.target.value))}
             />
           </label>
         </div>

         {lastCapture && (
           <Card className={styles.lastCapture}>
             <h4>Last Capture</h4>
             <img
               src={`/api/v1/storage/files/${encodeURIComponent(lastCapture.path)}`}
               alt="Last capture"
             />
             <p>{lastCapture.filename}</p>
             <a
               href={`/api/v1/storage/files/${encodeURIComponent(lastCapture.path)}`}
               download
             >
               Download
             </a>
           </Card>
         )}
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Capture button triggers API
- [ ] Quality setting works
- [ ] Last capture displayed
- [ ] Download link works

---

## Phase 6: Record Tab

### Goal
Video recording controls.

### Tasks

1. **Create `src/pages/Camera/RecordTab.tsx`**
   ```typescript
   import { useState, useEffect } from 'react';
   import { useMutation } from '@tanstack/react-query';
   import { api } from '@/api/client';
   import { Button } from '@/components/common/Button';
   import styles from './RecordTab.module.css';

   interface RecordTabProps {
     cameraId: number;
   }

   export function RecordTab({ cameraId }: RecordTabProps) {
     const [isRecording, setIsRecording] = useState(false);
     const [duration, setDuration] = useState(0);
     const [bitrate, setBitrate] = useState(4000000);

     const startRecording = useMutation({
       mutationFn: () =>
         api.post(`/api/v1/cameras/${cameraId}/record/start`, { bitrate }),
       onSuccess: () => setIsRecording(true),
     });

     const stopRecording = useMutation({
       mutationFn: () =>
         api.post(`/api/v1/cameras/${cameraId}/record/stop`),
       onSuccess: () => {
         setIsRecording(false);
         setDuration(0);
       },
     });

     useEffect(() => {
       let interval: NodeJS.Timeout;
       if (isRecording) {
         interval = setInterval(() => {
           setDuration((d) => d + 1);
         }, 1000);
       }
       return () => clearInterval(interval);
     }, [isRecording]);

     const formatDuration = (seconds: number) => {
       const h = Math.floor(seconds / 3600);
       const m = Math.floor((seconds % 3600) / 60);
       const s = seconds % 60;
       return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
     };

     return (
       <div className={styles.tab}>
         {isRecording ? (
           <>
             <div className={styles.recording}>
               <span className={styles.indicator}>● REC</span>
               <span className={styles.timer}>{formatDuration(duration)}</span>
             </div>
             <Button
               size="lg"
               variant="danger"
               onClick={() => stopRecording.mutate()}
               disabled={stopRecording.isPending}
             >
               ⏹ Stop Recording
             </Button>
           </>
         ) : (
           <>
             <Button
               size="lg"
               onClick={() => startRecording.mutate()}
               disabled={startRecording.isPending}
             >
               ⏺ Start Recording
             </Button>

             <div className={styles.settings}>
               <label>
                 Bitrate
                 <select
                   value={bitrate}
                   onChange={(e) => setBitrate(Number(e.target.value))}
                 >
                   <option value={2000000}>Low (2 Mbps)</option>
                   <option value={4000000}>Medium (4 Mbps)</option>
                   <option value={8000000}>High (8 Mbps)</option>
                 </select>
               </label>
             </div>
           </>
         )}
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Start/stop buttons work
- [ ] Recording timer displays
- [ ] Bitrate settings applied
- [ ] Visual recording indicator

---

## Phase 7: Timelapse Tab

### Goal
Timelapse capture controls.

### Tasks

1. **Create `src/pages/Camera/TimelapseTab.tsx`**
   ```typescript
   import { useState } from 'react';
   import { useMutation } from '@tanstack/react-query';
   import { api } from '@/api/client';
   import { Button } from '@/components/common/Button';
   import { Input } from '@/components/common/Input';
   import styles from './TimelapseTab.module.css';

   interface TimelapseTabProps {
     cameraId: number;
   }

   export function TimelapseTab({ cameraId }: TimelapseTabProps) {
     const [isActive, setIsActive] = useState(false);
     const [frameCount, setFrameCount] = useState(0);
     const [interval, setInterval] = useState(10); // seconds
     const [totalFrames, setTotalFrames] = useState(100);

     const startTimelapse = useMutation({
       mutationFn: () =>
         api.post(`/api/v1/cameras/${cameraId}/timelapse/start`, {
           interval,
           total_frames: totalFrames,
         }),
       onSuccess: () => setIsActive(true),
     });

     const stopTimelapse = useMutation({
       mutationFn: () =>
         api.post(`/api/v1/cameras/${cameraId}/timelapse/stop`),
       onSuccess: () => {
         setIsActive(false);
         setFrameCount(0);
       },
     });

     return (
       <div className={styles.tab}>
         {isActive ? (
           <>
             <div className={styles.progress}>
               <span>Frames: {frameCount} / {totalFrames}</span>
               <progress value={frameCount} max={totalFrames} />
             </div>
             <Button
               size="lg"
               variant="danger"
               onClick={() => stopTimelapse.mutate()}
             >
               ⏹ Stop Timelapse
             </Button>
           </>
         ) : (
           <>
             <Button
               size="lg"
               onClick={() => startTimelapse.mutate()}
               disabled={startTimelapse.isPending}
             >
               ⏱ Start Timelapse
             </Button>

             <div className={styles.settings}>
               <Input
                 label="Interval (seconds)"
                 type="number"
                 min={1}
                 value={interval}
                 onChange={(e) => setInterval(Number(e.target.value))}
               />
               <Input
                 label="Total Frames"
                 type="number"
                 min={1}
                 value={totalFrames}
                 onChange={(e) => setTotalFrames(Number(e.target.value))}
               />
               <p className={styles.estimate}>
                 Total duration: ~{Math.round((interval * totalFrames) / 60)} minutes
               </p>
             </div>
           </>
         )}
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Start/stop works
- [ ] Progress displayed
- [ ] Settings configurable
- [ ] Duration estimate shown

---

## Phase 8: Status & Feedback

### Goal
Toast notifications and confirmations.

### Tasks

1. Add toast notifications for:
   - Capture success/failure
   - Recording started/stopped
   - Timelapse progress/completion

2. Add confirmation dialogs for:
   - Stop recording
   - Stop timelapse

### Acceptance Criteria
- [ ] Toasts appear on actions
- [ ] Confirmations prevent accidents
- [ ] Errors displayed clearly

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| LivePreview | Unit | States, reconnection |
| CaptureTab | Unit | Mutation, display |
| RecordTab | Unit | Timer, states |
| TimelapseTab | Unit | Progress, settings |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/08-camera-tabs.md`
