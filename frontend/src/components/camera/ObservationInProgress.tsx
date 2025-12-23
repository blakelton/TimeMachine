/**
 * Component showing an observation in progress with status, progress, and controls
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { Modal } from "../Modal";
import { useToast } from "../../contexts/ToastContext";
import "./ObservationInProgress.css";

interface ObservationInProgressProps {
  observationId: number;
  cameraId: number;
  onStopped: () => void;
}

interface ObservationStatus {
  id: number;
  observation_type: string;
  status: string;
  progress: {
    current: number;
    total: number | null;
    percentage: number | null;
  };
  size_bytes: number;
  size_formatted: string;
  elapsed_seconds: number;
  has_preview: boolean;
}

function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hrs > 0) {
    return `${hrs}h ${mins}m ${secs}s`;
  } else if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
}

export function ObservationInProgress({
  observationId,
  cameraId,
  onStopped,
}: ObservationInProgressProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [previewTimestamp, setPreviewTimestamp] = useState(Date.now());
  // Track previous preview state to detect when it first becomes available
  const [_lastPreviewState, setLastPreviewState] = useState(false);

  // Poll for observation status
  const { data: status, isError, error } = useQuery<ObservationStatus>({
    queryKey: ["observationStatus", observationId],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/observations/{observation_id}/status" as any,
        {
          params: { path: { observation_id: observationId } },
        }
      );
      if (error) throw error;

      const result = data as ObservationStatus;

      // Update preview timestamp when has_preview becomes true (initial preview)
      // or periodically (every 10 seconds) when preview already exists
      if (result.has_preview) {
        setLastPreviewState((wasTrue) => {
          if (!wasTrue) {
            // Preview just became available - refresh immediately
            setPreviewTimestamp(Date.now());
          } else {
            // Preview already existed - refresh every 10 seconds
            setPreviewTimestamp((prev) => {
              const now = Date.now();
              return now - prev > 10000 ? now : prev;
            });
          }
          return true;
        });
      } else {
        setLastPreviewState(false);
      }

      return result;
    },
    refetchInterval: 2000,
    retry: 3,
    retryDelay: 1000,
  });

  // Stop mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST(
        "/api/v1/observations/{observation_id}/stop" as any,
        {
          params: { path: { observation_id: observationId } },
          body: { assemble_video: true },
        }
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (data: any) => {
      toast.success(data?.message || "Observation stopped");
      queryClient.invalidateQueries({ queryKey: ["activeJobs", cameraId] });
      queryClient.invalidateQueries({
        queryKey: ["activeObservation", cameraId],
      });
      setShowStopConfirm(false);
      onStopped();
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to stop observation");
    },
  });

  // Generate preview mutation (timelapse only)
  const generatePreviewMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `/api/v1/observations/${observationId}/generate-preview`,
        { method: "POST" }
      );
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to generate preview");
      }
      return response.json();
    },
    onSuccess: (data: { success: boolean; message: string }) => {
      if (data.success) {
        toast.success("Preview generated");
        // Update timestamp to force video reload
        setPreviewTimestamp(Date.now());
        // Refresh status to update has_preview
        queryClient.invalidateQueries({
          queryKey: ["observationStatus", observationId],
        });
      } else {
        toast.error(data.message || "Failed to generate preview");
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to generate preview");
    },
  });

  if (isError) {
    return (
      <div className="observation-progress observation-progress--error">
        <span className="observation-progress__error-icon">⚠️</span>
        <span>Error loading status: {(error as Error)?.message || "Unknown error"}</span>
        <Button variant="secondary" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: ["observationStatus", observationId] })}>
          Retry
        </Button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="observation-progress observation-progress--loading">
        <div className="observation-progress__loading-spinner" />
        <span>Loading observation status...</span>
      </div>
    );
  }

  const isTimelapse = status.observation_type === "timelapse";
  const progressText = isTimelapse
    ? status.progress.total
      ? `${status.progress.current} / ${status.progress.total} frames`
      : `${status.progress.current} frames`
    : formatDuration(status.progress.current);

  return (
    <>
      <div className="observation-progress">
        <div className="observation-progress__header">
          <div className="observation-progress__indicator" />
          <span className="observation-progress__title">
            {isTimelapse ? "TIMELAPSE" : "RECORDING"} IN PROGRESS
          </span>
        </div>

        <div className="observation-progress__stats">
          {/* Type and Progress */}
          <div className="observation-progress__stat">
            <span className="observation-progress__stat-label">Progress</span>
            <span className="observation-progress__stat-value">
              {progressText}
            </span>
          </div>

          {/* Progress Bar */}
          {status.progress.percentage !== null && (
            <div className="observation-progress__bar-container">
              <div
                className="observation-progress__bar"
                style={{ width: `${Math.min(status.progress.percentage, 100)}%` }}
              />
              <span className="observation-progress__bar-label">
                {status.progress.percentage.toFixed(1)}%
              </span>
            </div>
          )}

          {/* Elapsed Time */}
          <div className="observation-progress__stat">
            <span className="observation-progress__stat-label">Elapsed</span>
            <span className="observation-progress__stat-value">
              {formatDuration(status.elapsed_seconds)}
            </span>
          </div>

          {/* Size */}
          <div className="observation-progress__stat">
            <span className="observation-progress__stat-label">Size</span>
            <span className="observation-progress__stat-value">
              {status.size_formatted}
            </span>
          </div>
        </div>

        {/* Preview Video (timelapse only) */}
        {isTimelapse && status.has_preview && (
          <div className="observation-progress__preview">
            <video
              src={`/api/v1/observations/${observationId}/preview?t=${previewTimestamp}`}
              controls
              muted
              className="observation-progress__video"
            />
          </div>
        )}

        {/* Action Buttons */}
        <div className="observation-progress__actions">
          {/* Generate Preview (timelapse only, when enough frames captured) */}
          {isTimelapse && status.progress.current >= 2 && (
            <Button
              variant="secondary"
              onClick={() => generatePreviewMutation.mutate()}
              disabled={generatePreviewMutation.isPending}
            >
              {generatePreviewMutation.isPending ? "Generating..." : "Generate Preview"}
            </Button>
          )}
          <Button
            variant="danger"
            onClick={() => setShowStopConfirm(true)}
            disabled={stopMutation.isPending}
          >
            Stop Observation
          </Button>
        </div>
      </div>

      {/* Stop Confirmation Modal */}
      <Modal
        isOpen={showStopConfirm}
        onClose={() => setShowStopConfirm(false)}
        title="Stop Observation?"
        width="sm"
      >
        <div className="observation-progress__confirm">
          <p>
            {isTimelapse
              ? "This will stop the timelapse and assemble captured frames into a video."
              : "This will stop the recording and finalize the video file."}
          </p>
          <div className="observation-progress__confirm-actions">
            <Button
              variant="secondary"
              onClick={() => setShowStopConfirm(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
            >
              {stopMutation.isPending ? "Stopping..." : "Stop Observation"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
