/**
 * Banner shown when an interrupted timelapse is detected
 */

import { Button } from "../Button";
import "./TimelapseResumeBar.css";

export interface InterruptedTimelapse {
  job_id: number;
  frame_count: number;
  disk_usage_human: string;
  started_at: string | null;
  interrupted_at: string | null;
  original_config: {
    interval_seconds?: number;
    total_frames?: number;
    quality?: number;
  } | null;
}

interface TimelapseResumeBarProps {
  interrupted: InterruptedTimelapse;
  onResume: () => void;
  onFinalize: () => void;
  onCleanup: () => void;
  loading?: boolean;
}

export function TimelapseResumeBar({
  interrupted,
  onResume,
  onFinalize,
  onCleanup,
  loading = false,
}: TimelapseResumeBarProps) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Unknown";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="timelapse-resume-bar">
      <div className="timelapse-resume-bar__icon">!</div>
      <div className="timelapse-resume-bar__content">
        <div className="timelapse-resume-bar__title">
          Interrupted Timelapse Detected
        </div>
        <div className="timelapse-resume-bar__info">
          <span>{interrupted.frame_count} frames captured</span>
          <span className="timelapse-resume-bar__separator">-</span>
          <span>{interrupted.disk_usage_human}</span>
          <span className="timelapse-resume-bar__separator">-</span>
          <span>Started: {formatDate(interrupted.started_at)}</span>
        </div>
      </div>
      <div className="timelapse-resume-bar__actions">
        <Button
          variant="primary"
          size="sm"
          onClick={onResume}
          disabled={loading}
        >
          Resume
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={onFinalize}
          disabled={loading}
        >
          Create Video
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={onCleanup}
          disabled={loading}
        >
          Discard
        </Button>
      </div>
    </div>
  );
}
