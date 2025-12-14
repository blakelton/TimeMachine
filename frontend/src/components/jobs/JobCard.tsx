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

export function JobCard({
  job,
  cameraName,
  onViewOutput,
  compact = false,
}: JobCardProps) {
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
          <Button size="sm" variant="secondary" onClick={() => onViewOutput(job)}>
            View: {getOutputFilename()}
          </Button>
        </div>
      )}
    </div>
  );
}
