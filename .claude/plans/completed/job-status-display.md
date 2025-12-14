# Feature: JobStatusDisplay - Centralized Job Tracking UI

## Overview
Implement a JobStatusDisplay component that shows the status of current and recent jobs (recordings, timelapses, captures) for a camera. This provides users visibility into running operations and their history.

## Current State

**Backend**:
- Jobs API exists (`/api/v1/jobs`)
- WebSocket broadcasts `job_update` messages
- Jobs have: id, camera_id, job_type, status, progress, started_at, completed_at, output_path

**Frontend**:
- RecordTab/TimelapseTab handle `job_update` locally for their own status
- No centralized job display
- No job history visible to user
- No way to see jobs across tabs

## Requirements

### Functional Requirements
- FR1: Display list of jobs for a camera (or all cameras)
- FR2: Show real-time status updates via WebSocket
- FR3: Display progress bar for running jobs
- FR4: Show job type, status, duration, output file
- FR5: Filter by status (running, completed, failed)
- FR6: Link to output file when job completes
- FR7: Cancel running jobs (if supported)
- FR8: Auto-refresh on WebSocket reconnect

### Non-Functional Requirements
- NFR1: Real-time updates (<1s latency)
- NFR2: Limit displayed jobs (last 10)
- NFR3: Accessible progress indicators
- NFR4: Mobile-friendly layout

## Component Design

### JobStatusDisplay Component

```tsx
interface JobStatusDisplayProps {
  cameraId?: number;        // Optional: filter by camera
  showCompleted?: boolean;  // Show completed jobs (default: true)
  maxJobs?: number;         // Max jobs to display (default: 10)
  compact?: boolean;        // Compact mode for sidebar (default: false)
}
```

### File Structure

```
frontend/src/components/jobs/
├── JobStatusDisplay.tsx
├── JobStatusDisplay.css
├── JobCard.tsx
├── JobCard.css
├── JobProgress.tsx
├── JobProgress.css
└── index.ts
```

## Implementation Plan

### Phase 1: Core Components

**Task 1.1: Create JobProgress component**

File: `frontend/src/components/jobs/JobProgress.tsx`

```tsx
/**
 * Progress bar component for jobs
 */

import "./JobProgress.css";

interface JobProgressProps {
  progress: number;  // 0-100
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  showLabel?: boolean;
}

export function JobProgress({ progress, status, showLabel = true }: JobProgressProps) {
  const getStatusClass = () => {
    switch (status) {
      case "running":
        return "job-progress--running";
      case "completed":
        return "job-progress--completed";
      case "failed":
        return "job-progress--failed";
      case "interrupted":
        return "job-progress--interrupted";
      default:
        return "job-progress--pending";
    }
  };

  return (
    <div className={`job-progress ${getStatusClass()}`}>
      <div className="job-progress__bar">
        <div
          className="job-progress__fill"
          style={{ width: `${Math.min(progress, 100)}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {showLabel && (
        <span className="job-progress__label">
          {status === "running" ? `${progress.toFixed(0)}%` : status}
        </span>
      )}
    </div>
  );
}
```

**Task 1.2: Create JobCard component**

File: `frontend/src/components/jobs/JobCard.tsx`

```tsx
/**
 * Card component for displaying a single job
 */

import { JobProgress } from "./JobProgress";
import { Button } from "../Button";
import "./JobCard.css";

export interface Job {
  id: number;
  camera_id: number;
  job_type: "recording" | "timelapse" | "capture";
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  progress: number | null;
  started_at: string | null;
  completed_at: string | null;
  output_path: string | null;
  error_message: string | null;
}

interface JobCardProps {
  job: Job;
  cameraName?: string;
  onViewOutput?: (job: Job) => void;
  compact?: boolean;
}

export function JobCard({ job, cameraName, onViewOutput, compact = false }: JobCardProps) {
  const getJobTypeIcon = () => {
    switch (job.job_type) {
      case "recording":
        return "🎬";
      case "timelapse":
        return "⏱️";
      case "capture":
        return "📷";
    }
  };

  const getJobTypeLabel = () => {
    switch (job.job_type) {
      case "recording":
        return "Recording";
      case "timelapse":
        return "Timelapse";
      case "capture":
        return "Capture";
    }
  };

  const getStatusBadgeClass = () => {
    switch (job.status) {
      case "running":
        return "job-card__badge--running";
      case "completed":
        return "job-card__badge--completed";
      case "failed":
        return "job-card__badge--failed";
      case "interrupted":
        return "job-card__badge--interrupted";
      default:
        return "job-card__badge--pending";
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString();
  };

  const formatDuration = () => {
    if (!job.started_at) return null;
    const start = new Date(job.started_at);
    const end = job.completed_at ? new Date(job.completed_at) : new Date();
    const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getOutputFilename = () => {
    if (!job.output_path) return null;
    return job.output_path.split("/").pop();
  };

  if (compact) {
    return (
      <div className="job-card job-card--compact">
        <span className="job-card__icon">{getJobTypeIcon()}</span>
        <span className="job-card__type">{getJobTypeLabel()}</span>
        <span className={`job-card__badge ${getStatusBadgeClass()}`}>
          {job.status}
        </span>
        {job.status === "running" && job.progress !== null && (
          <JobProgress progress={job.progress} status={job.status} showLabel={false} />
        )}
      </div>
    );
  }

  return (
    <div className="job-card">
      <div className="job-card__header">
        <div className="job-card__title">
          <span className="job-card__icon">{getJobTypeIcon()}</span>
          <span className="job-card__type">{getJobTypeLabel()}</span>
          {cameraName && (
            <span className="job-card__camera">• {cameraName}</span>
          )}
        </div>
        <span className={`job-card__badge ${getStatusBadgeClass()}`}>
          {job.status}
        </span>
      </div>

      {job.status === "running" && job.progress !== null && (
        <div className="job-card__progress">
          <JobProgress progress={job.progress} status={job.status} />
        </div>
      )}

      <div className="job-card__details">
        <div className="job-card__detail">
          <span className="job-card__label">Started:</span>
          <span className="job-card__value">{formatDate(job.started_at)}</span>
        </div>
        {job.completed_at && (
          <div className="job-card__detail">
            <span className="job-card__label">Completed:</span>
            <span className="job-card__value">{formatDate(job.completed_at)}</span>
          </div>
        )}
        {formatDuration() && (
          <div className="job-card__detail">
            <span className="job-card__label">Duration:</span>
            <span className="job-card__value">{formatDuration()}</span>
          </div>
        )}
      </div>

      {job.status === "failed" && job.error_message && (
        <div className="job-card__error">
          <strong>Error:</strong> {job.error_message}
        </div>
      )}

      {job.status === "completed" && job.output_path && onViewOutput && (
        <div className="job-card__actions">
          <Button size="sm" variant="outline" onClick={() => onViewOutput(job)}>
            View: {getOutputFilename()}
          </Button>
        </div>
      )}
    </div>
  );
}
```

### Phase 2: Main Component

**Task 2.1: Create JobStatusDisplay**

File: `frontend/src/components/jobs/JobStatusDisplay.tsx`

```tsx
/**
 * Job status display component showing current and recent jobs
 */

import { useState, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { wsClient } from "../../lib/websocket";
import { useWebSocketMessage } from "../../hooks/useWebSocket";
import type { WSJobUpdate } from "../../types/websocket";
import { JobCard, type Job } from "./JobCard";
import { Button } from "../Button";
import "./JobStatusDisplay.css";

type StatusFilter = "all" | "running" | "completed" | "failed";

interface JobStatusDisplayProps {
  cameraId?: number;
  showCompleted?: boolean;
  maxJobs?: number;
  compact?: boolean;
  onViewOutput?: (job: Job) => void;
}

export function JobStatusDisplay({
  cameraId,
  showCompleted = true,
  maxJobs = 10,
  compact = false,
  onViewOutput,
}: JobStatusDisplayProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const queryClient = useQueryClient();

  // Fetch jobs
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["jobs", cameraId, maxJobs],
    queryFn: async () => {
      const params: Record<string, any> = { limit: maxJobs };
      if (cameraId) {
        params.camera_id = cameraId;
      }

      const response = await apiClient.GET("/api/v1/jobs" as any, {
        params: { query: params },
      });

      if (response.error) throw new Error("Failed to fetch jobs");
      return response.data as { jobs: Job[]; total: number };
    },
    refetchInterval: 30000, // Refetch every 30s as fallback
  });

  // Handle WebSocket job updates
  const handleJobUpdate = useCallback(
    (message: WSJobUpdate) => {
      // Only update if this job is relevant (no filter or matches camera)
      if (cameraId && message.camera_id !== cameraId) {
        return;
      }

      // Invalidate and refetch to get latest data
      queryClient.invalidateQueries({ queryKey: ["jobs", cameraId] });
    },
    [cameraId, queryClient]
  );

  useWebSocketMessage<WSJobUpdate>(wsClient, "job_update", handleJobUpdate);

  // Filter jobs based on status
  const filteredJobs = (data?.jobs || []).filter((job) => {
    if (!showCompleted && job.status === "completed") {
      return false;
    }
    if (statusFilter === "all") {
      return true;
    }
    if (statusFilter === "running") {
      return job.status === "running" || job.status === "pending";
    }
    return job.status === statusFilter;
  });

  // Count running jobs
  const runningCount = (data?.jobs || []).filter(
    (j) => j.status === "running" || j.status === "pending"
  ).length;

  if (compact) {
    return (
      <div className="job-status-display job-status-display--compact">
        {runningCount > 0 && (
          <div className="job-status-display__running-indicator">
            <span className="job-status-display__dot"></span>
            {runningCount} job{runningCount > 1 ? "s" : ""} running
          </div>
        )}
        {filteredJobs.slice(0, 3).map((job) => (
          <JobCard key={job.id} job={job} compact />
        ))}
      </div>
    );
  }

  return (
    <div className="job-status-display">
      <div className="job-status-display__header">
        <h3 className="job-status-display__title">
          Jobs
          {runningCount > 0 && (
            <span className="job-status-display__running-badge">
              {runningCount} running
            </span>
          )}
        </h3>
        <div className="job-status-display__filters">
          <Button
            size="sm"
            variant={statusFilter === "all" ? "primary" : "outline"}
            onClick={() => setStatusFilter("all")}
          >
            All
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "running" ? "primary" : "outline"}
            onClick={() => setStatusFilter("running")}
          >
            Running
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "completed" ? "primary" : "outline"}
            onClick={() => setStatusFilter("completed")}
          >
            Completed
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "failed" ? "primary" : "outline"}
            onClick={() => setStatusFilter("failed")}
          >
            Failed
          </Button>
        </div>
      </div>

      {isLoading && (
        <div className="job-status-display__loading">Loading jobs...</div>
      )}

      {error && (
        <div className="job-status-display__error">
          Failed to load jobs.
          <Button size="sm" variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {!isLoading && !error && filteredJobs.length === 0 && (
        <div className="job-status-display__empty">
          {statusFilter === "all"
            ? "No jobs yet"
            : `No ${statusFilter} jobs`}
        </div>
      )}

      {!isLoading && !error && filteredJobs.length > 0 && (
        <div className="job-status-display__list">
          {filteredJobs.map((job) => (
            <JobCard key={job.id} job={job} onViewOutput={onViewOutput} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### Phase 3: Integration

**Task 3.1: Add to CameraPage**

Update `frontend/src/pages/CameraPage.tsx` to include JobStatusDisplay:

```tsx
import { JobStatusDisplay } from "../components/jobs/JobStatusDisplay";

// In the render, add a jobs section:
<div className="camera-page__jobs">
  <JobStatusDisplay
    cameraId={cameraIdNum}
    maxJobs={5}
    onViewOutput={(job) => {
      // Navigate to appropriate tab or open file
      if (job.job_type === "recording") {
        navigate(`/camera/${cameraId}/record`);
      } else if (job.job_type === "timelapse") {
        navigate(`/camera/${cameraId}/timelapse`);
      }
    }}
  />
</div>
```

**Task 3.2: Optional - Add compact version to Layout sidebar**

Could add a compact job indicator in the header/sidebar showing running jobs across all cameras.

### Phase 4: Styling

**Task 4.1: Create CSS files**

Key styles:
- Running job pulsing indicator
- Progress bar animation
- Status badge colors (green/red/yellow/gray)
- Compact mode layout
- Filter button states
- Job list spacing

---

## CSS Example

File: `frontend/src/components/jobs/JobStatusDisplay.css`

```css
.job-status-display {
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.job-status-display__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.job-status-display__title {
  margin: 0;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.job-status-display__running-badge {
  background: var(--color-success);
  color: white;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: normal;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.job-status-display__filters {
  display: flex;
  gap: 0.25rem;
}

.job-status-display__list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.job-status-display__empty,
.job-status-display__loading,
.job-status-display__error {
  text-align: center;
  padding: 1rem;
  color: var(--text-muted);
}

/* Compact mode */
.job-status-display--compact {
  padding: 0.5rem;
  background: transparent;
}

.job-status-display__running-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.job-status-display__dot {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}
```

File: `frontend/src/components/jobs/JobCard.css`

```css
.job-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.75rem;
}

.job-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.job-card__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.job-card__icon {
  font-size: 1.25rem;
}

.job-card__type {
  font-weight: 500;
}

.job-card__camera {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.job-card__badge {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.job-card__badge--running {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.job-card__badge--completed {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.job-card__badge--failed {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.job-card__badge--pending {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.job-card__badge--interrupted {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.job-card__progress {
  margin: 0.5rem 0;
}

.job-card__details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.job-card__error {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--color-error-bg);
  color: var(--color-error);
  border-radius: 4px;
  font-size: 0.875rem;
}

.job-card__actions {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.5rem;
}

/* Compact mode */
.job-card--compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
}

.job-card--compact .job-card__badge {
  margin-left: auto;
}
```

---

## Testing Checklist

- [ ] Jobs list loads correctly
- [ ] Real-time updates via WebSocket work
- [ ] Progress bar updates during running jobs
- [ ] Status filter buttons work
- [ ] Camera filter works when cameraId provided
- [ ] Completed jobs show output file link
- [ ] Failed jobs show error message
- [ ] View output navigates correctly
- [ ] Empty state shows when no jobs
- [ ] Loading state shows while fetching
- [ ] Compact mode displays correctly
- [ ] Running jobs indicator pulses

---

**Status**: `.ready.md` - Ready for implementation
