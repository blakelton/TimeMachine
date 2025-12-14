# Home Dashboard - Plan

## Overview

Implement the Home tab with camera status cards, system stats graphs, and observation summary.

**Dependencies**: 05-frontend-foundation, 01-backend-foundation
**Estimated Duration**: 2 days

---

## Phase 1: Dashboard Layout

### Goal
Create responsive grid layout for dashboard content.

### Layout (Desktop)
```
+------------------------------------------+
|  Header                                   |
+------------------------------------------+
| Nav | +--------------------------------+ |
|     | | Camera Cards (grid)            | |
|     | +--------------------------------+ |
|     | | System Graphs | Observations   | |
|     | | CPU | RAM     | Recent list    | |
|     | +--------------------------------+ |
+------------------------------------------+
```

### Layout (Mobile)
```
+------------------+
| Header    [☰]    |
+------------------+
| Camera Card 1    |
| Camera Card 2    |
+------------------+
| CPU Graph        |
+------------------+
| RAM Graph        |
+------------------+
| Disk Usage       |
+------------------+
| Recent Files     |
+------------------+
```

### Tasks

1. **Create `src/pages/Home/index.tsx`**
   ```typescript
   import { CameraCards } from './CameraCards';
   import { SystemGraphs } from './SystemGraphs';
   import { ObservationSummary } from './ObservationSummary';
   import styles from './Home.module.css';

   export default function Home() {
     return (
       <div className={styles.dashboard}>
         <section className={styles.cameras}>
           <h2>Cameras</h2>
           <CameraCards />
         </section>
         
         <section className={styles.stats}>
           <h2>System</h2>
           <SystemGraphs />
         </section>
         
         <section className={styles.observations}>
           <h2>Recent Activity</h2>
           <ObservationSummary />
         </section>
       </div>
     );
   }
   ```

2. **Create responsive CSS**
   ```css
   .dashboard {
     display: grid;
     gap: var(--space-6);
     padding: var(--space-4);
   }

   @media (min-width: 1024px) {
     .dashboard {
       grid-template-columns: 1fr 1fr;
       grid-template-rows: auto 1fr;
     }
     
     .cameras {
       grid-column: 1 / -1;
     }
     
     .stats {
       grid-column: 1;
     }
     
     .observations {
       grid-column: 2;
     }
   }
   ```

### Acceptance Criteria
- [ ] Grid layout adapts to screen size
- [ ] Sections have proper headings
- [ ] Loading skeletons displayed

---

## Phase 2: Camera Status Cards

### Goal
Display status card for each configured camera.

### Card Design
```
+-------------------------+
| [📷] Camera Name        |
| Status: ● Online        |
|                         |
| [Thumbnail/Preview]     |
|                         |
| Res: 1920x1080 @ 30fps  |
| [View] [Capture]        |
+-------------------------+
```

### Tasks

1. **Create `src/pages/Home/CameraCards.tsx`**
   ```typescript
   import { useCameras } from '@/api/hooks/useCameras';
   import { Card } from '@/components/common/Card';
   import { Button } from '@/components/common/Button';
   import { Link } from 'react-router-dom';
   import styles from './CameraCards.module.css';

   type CameraStatus = 'online' | 'offline' | 'recording' | 'error';

   interface CameraCardProps {
     camera: {
       id: number;
       name: string;
       resolution: string;
       fps: number;
       enabled: boolean;
     };
     status: CameraStatus;
   }

   function CameraCard({ camera, status }: CameraCardProps) {
     const statusColors: Record<CameraStatus, string> = {
       online: 'var(--color-success)',
       offline: 'var(--color-text-secondary)',
       recording: 'var(--color-error)',
       error: 'var(--color-warning)',
     };

     return (
       <Card className={styles.card}>
         <div className={styles.header}>
           <span className={styles.icon}>📷</span>
           <span className={styles.name}>{camera.name}</span>
           <span
             className={styles.status}
             style={{ color: statusColors[status] }}
           >
             ● {status}
           </span>
         </div>
         
         <div className={styles.preview}>
           {status === 'online' ? (
             <img
               src={`/api/v1/cameras/${camera.id}/thumbnail`}
               alt={camera.name}
               loading="lazy"
             />
           ) : (
             <div className={styles.offline}>No Signal</div>
           )}
         </div>
         
         <div className={styles.info}>
           {camera.resolution} @ {camera.fps}fps
         </div>
         
         <div className={styles.actions}>
           <Link to={`/camera/${camera.id}`}>
             <Button size="sm">View</Button>
           </Link>
           <Button size="sm" variant="secondary">
             Capture
           </Button>
         </div>
       </Card>
     );
   }

   export function CameraCards() {
     const { data: cameras, isLoading } = useCameras();

     if (isLoading) {
       return <div className={styles.grid}>Loading...</div>;
     }

     if (!cameras?.length) {
       return (
         <Card>
           <p>No cameras configured.</p>
           <Link to="/system/cameras">
             <Button>Add Camera</Button>
           </Link>
         </Card>
       );
     }

     return (
       <div className={styles.grid}>
         {cameras.map((camera) => (
           <CameraCard
             key={camera.id}
             camera={camera}
             status={camera.enabled ? 'online' : 'offline'}
           />
         ))}
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Cards show camera info
- [ ] Status indicator reflects state
- [ ] Quick actions work
- [ ] Empty state displayed

---

## Phase 3: System Stats Graphs

### Goal
Display real-time CPU, RAM, and disk usage graphs.

### Tasks

1. **Install chart library**
   ```bash
   npm install chart.js react-chartjs-2
   ```

2. **Create `src/pages/Home/SystemGraphs.tsx`**
   ```typescript
   import { useState, useEffect, useRef } from 'react';
   import { Line, Doughnut } from 'react-chartjs-2';
   import {
     Chart as ChartJS,
     CategoryScale,
     LinearScale,
     PointElement,
     LineElement,
     ArcElement,
     Title,
     Tooltip,
     Legend,
   } from 'chart.js';
   import { useStats } from '@/api/hooks/useStats';
   import { Card } from '@/components/common/Card';
   import styles from './SystemGraphs.module.css';

   ChartJS.register(
     CategoryScale,
     LinearScale,
     PointElement,
     LineElement,
     ArcElement,
     Title,
     Tooltip,
     Legend
   );

   const MAX_POINTS = 60;

   export function SystemGraphs() {
     const { data: stats } = useStats();
     const [cpuHistory, setCpuHistory] = useState<number[]>([]);
     const [ramHistory, setRamHistory] = useState<number[]>([]);
     const labelsRef = useRef<string[]>([]);

     useEffect(() => {
       if (stats) {
         setCpuHistory((prev) => {
           const next = [...prev, stats.cpu_percent];
           return next.slice(-MAX_POINTS);
         });
         setRamHistory((prev) => {
           const next = [...prev, stats.memory_percent];
           return next.slice(-MAX_POINTS);
         });
         labelsRef.current = Array.from(
           { length: Math.max(cpuHistory.length, 1) },
           (_, i) => ''
         );
       }
     }, [stats]);

     const lineOptions = {
       responsive: true,
       maintainAspectRatio: false,
       scales: {
         y: { min: 0, max: 100 },
       },
       plugins: {
         legend: { display: false },
       },
       animation: { duration: 0 },
     };

     return (
       <div className={styles.graphs}>
         <Card className={styles.graph}>
           <h3>CPU Usage: {stats?.cpu_percent.toFixed(1)}%</h3>
           <div className={styles.chartContainer}>
             <Line
               data={{
                 labels: labelsRef.current,
                 datasets: [
                   {
                     data: cpuHistory,
                     borderColor: 'var(--color-primary)',
                     tension: 0.2,
                     pointRadius: 0,
                   },
                 ],
               }}
               options={lineOptions}
             />
           </div>
         </Card>

         <Card className={styles.graph}>
           <h3>RAM Usage: {stats?.memory_percent.toFixed(1)}%</h3>
           <div className={styles.chartContainer}>
             <Line
               data={{
                 labels: labelsRef.current,
                 datasets: [
                   {
                     data: ramHistory,
                     borderColor: 'var(--color-success)',
                     tension: 0.2,
                     pointRadius: 0,
                   },
                 ],
               }}
               options={lineOptions}
             />
           </div>
         </Card>

         <Card className={styles.disk}>
           <h3>Disk Usage</h3>
           <div className={styles.diskInfo}>
             <Doughnut
               data={{
                 labels: ['Used', 'Free'],
                 datasets: [
                   {
                     data: [
                       stats?.disk.used_gb || 0,
                       stats?.disk.free_gb || 0,
                     ],
                     backgroundColor: [
                       'var(--color-warning)',
                       'var(--color-bg-secondary)',
                     ],
                   },
                 ],
               }}
               options={{ plugins: { legend: { position: 'bottom' } } }}
             />
             <p>
               {stats?.disk.free_gb.toFixed(1)} GB free of{' '}
               {stats?.disk.total_gb.toFixed(1)} GB
             </p>
           </div>
         </Card>

         {stats?.temperature_celsius && (
           <Card className={styles.temp}>
             <h3>Temperature</h3>
             <p className={styles.tempValue}>
               {stats.temperature_celsius.toFixed(1)}°C
             </p>
           </Card>
         )}
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] CPU/RAM graphs update in real-time
- [ ] Disk usage doughnut chart
- [ ] Temperature displayed when available
- [ ] Graphs don't cause memory leaks

---

## Phase 4: Observation Summary

### Goal
Show recent recordings, captures, and active jobs.

### Tasks

1. **Create `src/pages/Home/ObservationSummary.tsx`**
   ```typescript
   import { Card } from '@/components/common/Card';
   import styles from './ObservationSummary.module.css';

   interface FileItem {
     name: string;
     path: string;
     size_mb: number;
     created_at: string;
   }

   export function ObservationSummary() {
     // TODO: Hook up to storage API
     const recentFiles: FileItem[] = [];
     const activeJobs: { camera: string; type: string }[] = [];

     return (
       <div className={styles.summary}>
         <Card>
           <h3>Active Jobs</h3>
           {activeJobs.length ? (
             <ul className={styles.jobs}>
               {activeJobs.map((job, i) => (
                 <li key={i}>
                   {job.camera}: {job.type}
                 </li>
               ))}
             </ul>
           ) : (
             <p className={styles.empty}>No active jobs</p>
           )}
         </Card>

         <Card>
           <h3>Recent Recordings</h3>
           {recentFiles.length ? (
             <ul className={styles.files}>
               {recentFiles.map((file, i) => (
                 <li key={i}>
                   <span>{file.name}</span>
                   <span>{file.size_mb.toFixed(1)} MB</span>
                 </li>
               ))}
             </ul>
           ) : (
             <p className={styles.empty}>No recent recordings</p>
           )}
         </Card>
       </div>
     );
   }
   ```

### Acceptance Criteria
- [ ] Shows active recordings/timelapses
- [ ] Lists recent files
- [ ] Empty states handled

---

## Phase 5: Real-time Updates

### Goal
WebSocket integration for live stats.

### Tasks

1. **Create stats WebSocket hook**
   ```typescript
   import { useEffect } from 'react';
   import { useQueryClient } from '@tanstack/react-query';
   import { wsClient } from '@/api/websocket';

   export function useStatsWebSocket() {
     const queryClient = useQueryClient();

     useEffect(() => {
       wsClient.connect();

       const unsubscribe = wsClient.subscribe('stats_update', (data) => {
         queryClient.setQueryData(['stats'], data);
       });

       return () => {
         unsubscribe();
       };
     }, [queryClient]);
   }
   ```

2. **Integrate in Home page**

### Acceptance Criteria
- [ ] Stats update via WebSocket
- [ ] Fallback to polling if WS fails
- [ ] Reconnection works

---

## Phase 6: Error States

### Goal
Handle errors and warnings gracefully.

### Tasks

1. **Add warning banners for**
   - Low disk space (< 1GB)
   - Camera offline
   - High CPU/temperature

2. **Create `src/pages/Home/WarningBanner.tsx`**

### Acceptance Criteria
- [ ] Warnings displayed prominently
- [ ] Dismissible alerts
- [ ] Links to resolve issues

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| CameraCards | Unit | Rendering, states |
| SystemGraphs | Unit | Data updates |
| Dashboard layout | Integration | Responsive |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/06-home-dashboard.md`
