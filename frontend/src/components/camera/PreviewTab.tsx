/**
 * Preview tab - Live MJPEG camera preview
 *
 * Features:
 * - Auto-start preview when camera tab opens
 * - Exponential backoff retry for stream connection
 * - Automatic reconnection on stream errors
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./PreviewTab.css";

/** Retry configuration for stream connection */
const RETRY_CONFIG = {
  maxRetries: 5,
  initialDelayMs: 500,
  maxDelayMs: 4000,
  backoffMultiplier: 2,
};

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
  const [retryCount, setRetryCount] = useState(0);
  const [isConnecting, setIsConnecting] = useState(false);
  const [streamKey, setStreamKey] = useState(0); // Used to force img reload

  const imgRef = useRef<HTMLImageElement>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const toast = useToast();

  // Track mounted state for async operations
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      // Clear any pending retry timeout
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };
  }, []);

  const getStreamUrl = useCallback(() => {
    // Use relative URL - nginx will proxy to backend in production
    // Add cache-busting key to force reload on retry
    return `/api/v1/cameras/${cameraId}/preview/stream?t=${streamKey}`;
  }, [cameraId, streamKey]);

  /**
   * Calculate delay for exponential backoff
   */
  const getRetryDelay = useCallback((attempt: number): number => {
    const delay = RETRY_CONFIG.initialDelayMs * Math.pow(RETRY_CONFIG.backoffMultiplier, attempt);
    return Math.min(delay, RETRY_CONFIG.maxDelayMs);
  }, []);

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
   * Wait for stream to be ready by polling the stream endpoint
   * Returns true if stream becomes available within timeout
   */
  const waitForStreamReady = useCallback(async (): Promise<boolean> => {
    const baseUrl = `/api/v1/cameras/${cameraId}/preview/stream`;

    for (let attempt = 0; attempt < RETRY_CONFIG.maxRetries; attempt++) {
      if (!mountedRef.current) return false;

      try {
        // Try a HEAD request to check if stream is available
        const response = await fetch(baseUrl, {
          method: "HEAD",
          // Short timeout for each attempt
          signal: AbortSignal.timeout(2000),
        });

        if (response.ok) {
          return true;
        }
      } catch {
        // Stream not ready yet, continue retrying
      }

      // Wait with exponential backoff before next attempt
      const delay = getRetryDelay(attempt);
      await new Promise(resolve => {
        retryTimeoutRef.current = setTimeout(resolve, delay);
      });
      retryTimeoutRef.current = null;
    }

    return false;
  }, [cameraId, getRetryDelay]);

  /**
   * Start preview and wait for stream to be ready
   */
  const startPreviewWithRetry = useCallback(async (showToast: boolean = true) => {
    if (!mountedRef.current) return;

    setIsLoading(true);
    setIsConnecting(true);
    setHasError(false);
    setErrorMessage("");
    setRetryCount(0);

    try {
      // Start the preview pipeline
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

      // Wait for stream to be ready with retries
      setErrorMessage("Connecting to camera...");
      const streamReady = await waitForStreamReady();

      if (!mountedRef.current) return;

      if (streamReady) {
        setIsPreviewActive(true);
        setStreamKey(prev => prev + 1); // Force img reload
        setErrorMessage("");
        if (showToast) {
          toast.success("Preview started");
        }
      } else {
        // Stream didn't become ready, but pipeline might still be starting
        // Show preview anyway - the img onError handler will manage retries
        setIsPreviewActive(true);
        setStreamKey(prev => prev + 1);
        if (showToast) {
          toast.success("Preview starting...");
        }
      }
    } catch (error) {
      if (!mountedRef.current) return;

      const message =
        error instanceof Error ? error.message : "Failed to start preview";
      setErrorMessage(message);
      setHasError(true);
      if (showToast) {
        toast.error(message);
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
        setIsConnecting(false);
      }
    }
  }, [cameraId, waitForStreamReady, toast]);

  /**
   * Handle image load error with retry logic
   */
  const handleImageError = useCallback(() => {
    if (!mountedRef.current || !isPreviewActive) return;

    setRetryCount(prev => {
      const newCount = prev + 1;

      if (newCount <= RETRY_CONFIG.maxRetries) {
        // Schedule retry with exponential backoff
        const delay = getRetryDelay(newCount - 1);
        setErrorMessage(`Reconnecting... (attempt ${newCount}/${RETRY_CONFIG.maxRetries})`);

        retryTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current && isPreviewActive) {
            // Force image reload by updating the key
            setStreamKey(k => k + 1);
          }
        }, delay);
      } else {
        // Max retries exceeded
        setHasError(true);
        setErrorMessage("Stream connection lost. Click Reconnect to try again.");
      }

      return newCount;
    });
  }, [isPreviewActive, getRetryDelay]);

  /**
   * Handle successful image load - reset retry state
   */
  const handleImageLoad = useCallback(() => {
    if (!mountedRef.current) return;

    setHasError(false);
    setErrorMessage("");
    setRetryCount(0);
    setIsConnecting(false);

    // Clear any pending retry timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
  }, []);

  /**
   * Check preview status (used on mount)
   */
  const checkPreviewStatus = useCallback(async () => {
    try {
      const streamUrl = `/api/v1/cameras/${cameraId}/preview/stream`;
      const response = await fetch(streamUrl, {
        method: "HEAD",
        signal: AbortSignal.timeout(2000),
      });
      const previewActive = response.ok;
      setIsPreviewActive(previewActive);
      if (previewActive) {
        setStreamKey(prev => prev + 1);
      }
      return previewActive;
    } catch {
      setIsPreviewActive(false);
      return false;
    }
  }, [cameraId]);

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
          // No active observation - auto-start preview (silent, no toast)
          startPreviewWithRetry(false);
        }
      }
    };

    initializePreview();
  }, [checkPreviewStatus, autoStart, autoStartAttempted, checkForActiveObservation, startPreviewWithRetry]);

  // Reset state when camera changes
  useEffect(() => {
    setAutoStartAttempted(false);
    setRetryCount(0);
    setHasError(false);
    setErrorMessage("");
    setIsConnecting(false);

    // Clear any pending retry timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
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

  const handleStartPreview = () => {
    startPreviewWithRetry(true);
  };

  const handleStopPreview = async () => {
    setIsLoading(true);

    // Clear any pending retries
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

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
      setRetryCount(0);
      setHasError(false);
      setErrorMessage("");
      toast.success("Preview stopped");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to stop preview";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReconnect = () => {
    // Reset retry count and try again
    setRetryCount(0);
    setHasError(false);
    startPreviewWithRetry(true);
  };

  // Determine display message for connecting state
  const connectingMessage = isConnecting
    ? (errorMessage || "Connecting to camera...")
    : (retryCount > 0 && retryCount <= RETRY_CONFIG.maxRetries)
      ? errorMessage
      : "";

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
            {/* Show connecting overlay while retrying */}
            {connectingMessage && !hasError && (
              <div className="preview-tab__connecting-overlay">
                <div className="preview-tab__spinner" />
                <p>{connectingMessage}</p>
              </div>
            )}
            {/* Show error overlay when max retries exceeded */}
            {hasError && (
              <div className="preview-tab__error-overlay">
                <p>{errorMessage || "Stream connection lost"}</p>
                <Button variant="primary" onClick={handleReconnect}>
                  Reconnect
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="preview-tab__placeholder">
            {isLoading ? (
              <div className="preview-tab__loading">
                <div className="preview-tab__spinner" />
                <p>{errorMessage || "Starting camera..."}</p>
              </div>
            ) : hasError && errorMessage ? (
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
