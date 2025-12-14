/**
 * Preview tab - Live MJPEG camera preview
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./PreviewTab.css";

export interface PreviewTabProps {
  cameraId: number;
  /** Auto-start preview when component mounts (if no active observation running) */
  autoStart?: boolean;
}

export function PreviewTab({ cameraId, autoStart = false }: PreviewTabProps) {
  const [isPreviewActive, setIsPreviewActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [autoStartAttempted, setAutoStartAttempted] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const toast = useToast();

  const getStreamUrl = useCallback(() => {
    // Use relative URL - nginx will proxy to backend in production
    return `/api/v1/cameras/${cameraId}/preview/stream`;
  }, [cameraId]);

  /**
   * Check if camera has an active observation (recording or timelapse).
   * Returns true if there's an active job for this camera.
   */
  const checkForActiveObservation = useCallback(async (): Promise<boolean> => {
    try {
      const { data, error } = await apiClient.GET("/api/v1/jobs/running", {
        params: { query: { camera_id: cameraId } },
      });
      if (error || !data) return false;

      // Check if any running job belongs to this camera
      const jobs = data.jobs || [];
      return jobs.some(
        (job) => job.status === "running" || job.status === "pending"
      );
    } catch {
      return false;
    }
  }, [cameraId]);

  /**
   * Start preview silently (without toast notification).
   * Used for auto-start to avoid notification spam.
   */
  const startPreviewSilently = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    setErrorMessage("");

    try {
      const { error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/preview/start" as any,
        {
          params: { path: { camera_id: cameraId } },
        }
      );

      if (error) {
        const errorMsg = typeof error.detail === 'string' ? error.detail : "Failed to start preview";
        throw new Error(errorMsg);
      }

      setIsPreviewActive(true);
      // No toast for auto-start
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start preview";
      setErrorMessage(message);
      setHasError(true);
      // No toast for auto-start failures - just show in UI
    } finally {
      setIsLoading(false);
    }
  }, [cameraId]);

  /**
   * Check preview status and optionally auto-start if conditions are met.
   */
  const checkPreviewStatus = useCallback(async () => {
    try {
      // Try to load the preview stream to see if it's active
      const streamUrl = getStreamUrl();
      const response = await fetch(streamUrl, { method: "HEAD" });
      const previewActive = response.ok;
      setIsPreviewActive(previewActive);
      setHasError(!previewActive);
      return previewActive;
    } catch {
      setIsPreviewActive(false);
      setHasError(true);
      return false;
    }
  }, [getStreamUrl]);

  // Check if preview is already running on mount, and auto-start if configured
  useEffect(() => {
    const initializePreview = async () => {
      const previewAlreadyActive = await checkPreviewStatus();

      // Auto-start logic: only attempt once per mount
      if (autoStart && !previewAlreadyActive && !autoStartAttempted) {
        setAutoStartAttempted(true);

        // Check if there's an active observation running
        const hasActiveObservation = await checkForActiveObservation();

        if (!hasActiveObservation) {
          // No active observation - auto-start preview
          startPreviewSilently();
        }
      }
    };

    initializePreview();
  }, [checkPreviewStatus, autoStart, autoStartAttempted, checkForActiveObservation, startPreviewSilently]);

  // Reset auto-start attempted flag when camera changes
  useEffect(() => {
    setAutoStartAttempted(false);
  }, [cameraId]);

  /**
   * Cleanup effect: Stop preview when component unmounts.
   * This prevents orphaned preview streams from running indefinitely.
   */
  useEffect(() => {
    return () => {
      // Only attempt to stop if preview is active
      if (isPreviewActive) {
        // Fire-and-forget cleanup (don't await on unmount)
        apiClient.POST("/api/v1/cameras/{camera_id}/preview/stop" as any, {
          params: { path: { camera_id: cameraId } },
        });
      }
    };
  }, [isPreviewActive, cameraId]);

  const handleStartPreview = async () => {
    setIsLoading(true);
    setHasError(false);
    setErrorMessage("");

    try {
      const { error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/preview/start" as any,
        {
          params: { path: { camera_id: cameraId } },
        }
      );

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to start preview";
        throw new Error(errorMessage);
      }

      setIsPreviewActive(true);
      toast.success("Preview started");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start preview";
      setErrorMessage(message);
      setHasError(true);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopPreview = async () => {
    setIsLoading(true);

    try {
      const { error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/preview/stop" as any,
        {
          params: { path: { camera_id: cameraId } },
        }
      );

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to stop preview";
        throw new Error(errorMessage);
      }

      setIsPreviewActive(false);
      toast.success("Preview stopped");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to stop preview";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageError = () => {
    setHasError(true);
    setErrorMessage("Failed to load preview stream");
  };

  const handleImageLoad = () => {
    setHasError(false);
    setErrorMessage("");
  };

  return (
    <div className="preview-tab">
      <div className="preview-tab__controls">
        {!isPreviewActive ? (
          <Button
            variant="primary"
            onClick={handleStartPreview}
            disabled={isLoading}
          >
            {isLoading ? "Starting..." : "Start Preview"}
          </Button>
        ) : (
          <Button
            variant="secondary"
            onClick={handleStopPreview}
            disabled={isLoading}
          >
            {isLoading ? "Stopping..." : "Stop Preview"}
          </Button>
        )}
      </div>

      <div className="preview-tab__display">
        {isPreviewActive ? (
          <div className="preview-tab__stream">
            <img
              ref={imgRef}
              src={getStreamUrl()}
              alt="Camera preview"
              className="preview-tab__image"
              onError={handleImageError}
              onLoad={handleImageLoad}
            />
            {hasError && (
              <div className="preview-tab__error-overlay">
                <p>Stream connection lost</p>
                <Button variant="primary" onClick={handleStartPreview}>
                  Reconnect
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="preview-tab__placeholder">
            {hasError && errorMessage ? (
              <div className="preview-tab__error">
                <p>{errorMessage}</p>
                <Button variant="primary" onClick={handleStartPreview}>
                  Try Again
                </Button>
              </div>
            ) : (
              <p>Preview not running. Click "Start Preview" to begin.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
