/**
 * Camera preview card component with live feed and observation progress.
 *
 * Shows:
 * - Live MJPEG preview when camera is idle
 * - Timelapse progress + preview.mp4 when observation is running
 * - Graceful fallback when preview stream is unavailable
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { LiveThumbnail } from "./LiveThumbnail";
import type { CameraDashboardItem } from "../hooks/useCameraDashboard";
import "./CameraPreviewCard.css";

interface CameraPreviewCardProps {
  camera: CameraDashboardItem;
  /**
   * Optional key to force LiveThumbnail refresh after navigation.
   * Pass the dashboard timestamp to reset streams when data refreshes.
   */
  refreshKey?: string | null;
}

/**
 * CameraPreviewCard displays a camera tile with live preview or observation status.
 *
 * States:
 * - Idle + preview running: Shows live MJPEG stream
 * - Idle + no preview: Shows placeholder with camera icon
 * - Observation active: Shows progress bar and preview.mp4 if available
 * - Disabled: Muted appearance
 */
export function CameraPreviewCard({ camera, refreshKey }: CameraPreviewCardProps) {
  const {
    camera_id,
    name,
    camera_type,
    enabled,
    preview_state,
    preview_url,
    has_active_observation,
    observation,
  } = camera;


  // Track video preview timestamp for cache-busting
  // Refresh the video URL when frame count changes significantly
  const [previewTimestamp, setPreviewTimestamp] = useState(() => Date.now());
  const [lastFrameCount, setLastFrameCount] = useState(0);

  // Update preview timestamp when preview becomes available or new frames captured
  useEffect(() => {
    if (observation?.has_preview && observation?.progress_current) {
      const currentFrames = observation.progress_current;
      // Refresh every 15 frames (roughly 1 second of footage at 15fps)
      if (currentFrames - lastFrameCount >= 15 || lastFrameCount === 0) {
        setLastFrameCount(currentFrames);
        setPreviewTimestamp(Date.now());
      }
    }
  }, [observation?.has_preview, observation?.progress_current, lastFrameCount]);

  // Get combined status info (class, icon, text) to avoid duplication
  const getStatus = () => {
    if (!enabled) {
      return { className: "disabled", icon: "⏸️", text: "Disabled" };
    }
    if (has_active_observation && observation) {
      const isRecording = observation.observation_type === "recording";
      return {
        className: isRecording ? "recording" : "timelapse",
        icon: isRecording ? "🔴" : "⏱️",
        text: isRecording ? "Recording" : "Timelapse",
      };
    }
    return { className: "available", icon: "✅", text: "Available" };
  };

  const status = getStatus();

  // Calculate observation progress percentage
  const getProgressPercent = (): number => {
    if (!observation) return 0;
    if (!observation.progress_total || observation.progress_total === 0) {
      // Indeterminate progress - pulse animation
      return -1;
    }
    return Math.min(100, (observation.progress_current / observation.progress_total) * 100);
  };

  // Format progress text
  const getProgressText = (): string => {
    if (!observation) return "";
    if (observation.observation_type === "timelapse") {
      if (observation.progress_total) {
        return `${observation.progress_current}/${observation.progress_total} frames`;
      }
      return `${observation.progress_current} frames`;
    }
    // Recording - show duration
    return `${observation.progress_current}s`;
  };

  const progressPercent = getProgressPercent();

  return (
    <Link
      to={`/camera/${camera_id}`}
      className={`camera-preview-card ${status.className}`}
      aria-label={`${name} camera - ${status.text}. Click to view details.`}
    >
      {/* Preview Area */}
      <div className="preview-area">
        {/* Show live preview or observation preview */}
        {has_active_observation && observation?.has_preview && observation.preview_url ? (
          // Observation in progress with preview.mp4 available
          // Use key with timestamp to force reload when preview updates
          <video
            key={`preview-${observation.id}-${previewTimestamp}`}
            src={`${observation.preview_url}?t=${previewTimestamp}`}
            className="observation-preview"
            aria-label={`${name} observation preview`}
            autoPlay
            loop
            muted
            playsInline
          />
        ) : preview_state === "running" && preview_url ? (
          // Live MJPEG stream - key forces remount, refreshKey triggers state reset
          <LiveThumbnail
            key={`live-${camera_id}-${refreshKey ?? "default"}`}
            streamUrl={preview_url}
            alt={`${name} live preview`}
            fallbackIcon="📷"
            refreshKey={refreshKey ?? undefined}
          />
        ) : (
          // No preview available - show placeholder
          <div className="preview-placeholder">
            <span className="preview-placeholder-icon">
              {camera_type === "csi" ? "🎥" : "📷"}
            </span>
            {(preview_state === "error" || preview_state === "crashed") && (
              <span className="preview-error-text">Preview error</span>
            )}
            {preview_state === "starting" && (
              <span className="preview-error-text">Starting...</span>
            )}
          </div>
        )}

        {/* Observation progress overlay */}
        {has_active_observation && observation && (
          <div className="observation-overlay">
            <div className="observation-info">
              <span className="observation-type">
                {observation.observation_type === "timelapse" ? "Timelapse" : "Recording"}
              </span>
              <span className="observation-progress-text">{getProgressText()}</span>
            </div>
            <div className="progress-bar-container">
              <div
                className={`progress-bar-fill ${progressPercent < 0 ? "indeterminate" : ""}`}
                style={progressPercent >= 0 ? { width: `${progressPercent}%` } : undefined}
              />
            </div>
          </div>
        )}
      </div>

      {/* Card Footer */}
      <div className="card-footer">
        <div className="camera-info">
          <h3 className="camera-name">{name}</h3>
          <span className="camera-type-badge">{camera_type.toUpperCase()}</span>
        </div>
        <div className="camera-status">
          <span className="status-icon" aria-hidden="true">{status.icon}</span>
          <span className="status-text">{status.text}</span>
        </div>
      </div>
    </Link>
  );
}
