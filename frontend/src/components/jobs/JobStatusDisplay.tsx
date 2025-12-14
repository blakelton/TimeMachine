/**
 * Job status display component showing current and recent jobs
 */

import { useState, useCallback } from "react";
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
      const response = await apiClient.GET("/api/v1/jobs", {
        params: {
          query: {
            camera_id: cameraId,
            limit: maxJobs,
          },
        },
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
            variant={statusFilter === "all" ? "primary" : "secondary"}
            onClick={() => setStatusFilter("all")}
          >
            All
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "running" ? "primary" : "secondary"}
            onClick={() => setStatusFilter("running")}
          >
            Running
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "completed" ? "primary" : "secondary"}
            onClick={() => setStatusFilter("completed")}
          >
            Completed
          </Button>
          <Button
            size="sm"
            variant={statusFilter === "failed" ? "primary" : "secondary"}
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
          <Button size="sm" variant="secondary" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {!isLoading && !error && filteredJobs.length === 0 && (
        <div className="job-status-display__empty">
          {statusFilter === "all" ? "No jobs yet" : `No ${statusFilter} jobs`}
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
