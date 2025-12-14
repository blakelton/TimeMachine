/**
 * Progress bar component for jobs
 */

import "./JobProgress.css";

interface JobProgressProps {
  progress: number; // 0-100
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  showLabel?: boolean;
}

export function JobProgress({
  progress,
  status,
  showLabel = true,
}: JobProgressProps) {
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
