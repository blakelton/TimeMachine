/**
 * Observation tile component for displaying a single observation in the grid.
 */

import { memo } from "react";
import type { CompletedObservation } from "../../hooks/useObservations";
import { getThumbnailUrl } from "../../hooks/useObservations";
import "./ObservationTile.css";

interface ObservationTileProps {
  observation: CompletedObservation;
  onClick: () => void;
  selectionMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (id: number) => void;
}

/**
 * Format a date string for display
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format time from date string
 */
function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format duration in seconds to human readable
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

/**
 * Get type badge info
 */
function getTypeBadge(type: string): { label: string; className: string } {
  switch (type) {
    case "timelapse":
      return { label: "Timelapse", className: "badge--timelapse" };
    case "recording":
      return { label: "Recording", className: "badge--recording" };
    case "still":
      return { label: "Still", className: "badge--still" };
    default:
      return { label: type, className: "" };
  }
}

/**
 * Get status indicator
 */
function getStatusIndicator(status: string): { icon: string; className: string } {
  switch (status) {
    case "completed":
      return { icon: "", className: "status--completed" };
    case "stopped":
      return { icon: "", className: "status--stopped" };
    case "failed":
      return { icon: "", className: "status--failed" };
    default:
      return { icon: "", className: "" };
  }
}

export const ObservationTile = memo(function ObservationTile({
  observation,
  onClick,
  selectionMode = false,
  isSelected = false,
  onToggleSelect,
}: ObservationTileProps) {
  const badge = getTypeBadge(observation.observation_type);
  const status = getStatusIndicator(observation.status);
  const thumbnailUrl = getThumbnailUrl(observation.id);

  const handleClick = (e: React.MouseEvent) => {
    if (selectionMode && onToggleSelect) {
      e.stopPropagation();
      onToggleSelect(observation.id);
    } else {
      onClick();
    }
  };

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onToggleSelect) {
      onToggleSelect(observation.id);
    }
  };

  return (
    <div
      className={`observation-tile ${isSelected ? "observation-tile--selected" : ""}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
    >
      <div className="observation-tile__thumbnail">
        <img
          src={thumbnailUrl}
          alt={`${observation.observation_type} from ${observation.camera_name}`}
          loading="lazy"
        />
        <span className={`observation-tile__badge ${badge.className}`}>
          {badge.label}
        </span>
        {status.icon && (
          <span className={`observation-tile__status ${status.className}`}>
            {status.icon}
          </span>
        )}
        {/* Selection checkbox */}
        {(selectionMode || isSelected) && (
          <div
            className={`observation-tile__checkbox ${isSelected ? "observation-tile__checkbox--checked" : ""}`}
            onClick={handleCheckboxClick}
          >
            {isSelected && <span>✓</span>}
          </div>
        )}
      </div>

      <div className="observation-tile__info">
        <div className="observation-tile__camera">{observation.camera_name}</div>
        <div className="observation-tile__date">
          {formatDate(observation.started_at)} at {formatTime(observation.started_at)}
        </div>
        <div className="observation-tile__meta">
          <span className="observation-tile__duration">
            {formatDuration(observation.duration_seconds)}
          </span>
          {observation.frame_count && (
            <span className="observation-tile__frames">
              {observation.frame_count} frames
            </span>
          )}
          <span className="observation-tile__size">{observation.size_display}</span>
        </div>
        {observation.notes && (
          <div className="observation-tile__notes" title={observation.notes}>
            {observation.notes.length > 50
              ? `${observation.notes.substring(0, 50)}...`
              : observation.notes}
          </div>
        )}
      </div>
    </div>
  );
});
