/**
 * Preview tab - Live MJPEG camera preview
 *
 * Features:
 * - Auto-start preview when camera tab opens
 * - Exponential backoff retry for stream connection
 * - Automatic reconnection on stream errors
 * - Exposes control methods via ref for external control
 */

import { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import { startPreview, stopPreview, checkCameraHealth as checkCameraHealthApi } from "../../api";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./PreviewTab.css";

/** Retry configuration for stream connection */
const RETRY_CONFIG = {
  /** Max retries for image load failures */
  maxRetries: 5,
  /** Initial delay between retries (ms) */
  initialDelayMs: 200,
  /** Maximum delay between retries (ms) */
  maxDelayMs: 2000,
  /** Multiplier for exponential backoff */
  backoffMultiplier: 1.5,
  /** How long to poll for stream readiness after starting (ms) */
  streamReadyTimeout: 5000,
  /** Interval between stream ready checks (ms) */
  streamReadyInterval: 100,
};

export interface PreviewTabProps {
  cameraId: number;
  /** Auto-start preview when component mounts (if no active observation running) */
  autoStart?: boolean;
  /** Hide the internal start/stop controls (when controls are external) */
  hideControls?: boolean;
}

/** Handle exposed by PreviewTab for external control */
export interface PreviewTabHandle {
  startPreview: () => void;
  stopPreview: () => void;
  isPreviewActive: boolean;
  isLoading: boolean;
}

export const PreviewTab = forwardRef<PreviewTabHandle, PreviewTabProps>(function PreviewTab(
  { cameraId, autoStart = false, hideControls = false },
  ref
) {
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

  // Ref to hold the latest startPreviewWithRetry function
  // This avoids including it in effect dependencies which would cause re-runs
  const startPreviewRef = useRef<((showToast: boolean) => Promise<void>) | null>(null);

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
   * Check camera health and return a user-friendly error message if unhealthy.
   */
  const checkCameraHealth = useCallback(async (): Promise<string | null> => {
    try {
      const { data, error } = await checkCameraHealthApi(cameraId);

      if (error || !data) {
        return null; // Can't determine health, continue anyway
      }

      if (!data.healthy) {
        // Return user-friendly error based on the issue detected
        if (data.error?.includes("I2C")) {
          return "Camera connection error - please check the CSI ribbon cable is properly connected";
        }
        if (data.error?.includes("timed out")) {
          return "Camera is not responding - it may need to be reconnected or the Pi restarted";
        }
        if (!data.device_exists) {
          return "Camera device not found - the camera may be disconnected";
        }
        if (!data.device_accessible) {
          return "Cannot access camera - permission denied";
        }
        return data.error || "Camera is unhealthy";
      }

      return null; // Camera is healthy
    } catch {
      return null; // Can't determine health, continue anyway
    }
  }, [cameraId]);

  /**
   * Wait for stream to be ready by polling the preview status endpoint.
   * This is much faster than the old HEAD request approach which timed out.
   */
  const waitForStreamReady = useCallback(async (): Promise<boolean> => {
    const startTime = Date.now();
    const statusUrl = `/api/v1/cameras/${cameraId}/preview/status`;

    while (Date.now() - startTime < RETRY_CONFIG.streamReadyTimeout) {
      if (!mountedRef.current) return false;

      try {
        const response = await fetch(statusUrl, {
          signal: AbortSignal.timeout(1000),
        });

        if (response.ok) {
          const data = await response.json();
          // Check if the preview state is "running"
          if (data.state === "running") {
            return true;
          }
        }
      } catch {
        // Status check failed, continue polling
      }

      // Short fixed interval - no exponential backoff needed for status polling
      await new Promise(resolve => {
        retryTimeoutRef.current = setTimeout(resolve, RETRY_CONFIG.streamReadyInterval);
      });
      retryTimeoutRef.current = null;
    }

    // Timeout reached, but we'll still try to show the stream
    // The image onLoad/onError handlers will manage from here
    return false;
  }, [cameraId]);

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
      const { error } = await startPreview(cameraId);

      if (error) {
        const errorMsg = typeof error.detail === 'string' ? error.detail : "Failed to start preview";
        // "Already running" is not an error - treat it as success
        if (errorMsg.toLowerCase().includes("already running")) {
          // Preview is already running, just display it
          setIsPreviewActive(true);
          setStreamKey(prev => prev + 1);
          setIsLoading(false);
          setIsConnecting(false);
          return;
        }
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
        // Stream didn't become ready - check camera health for better error message
        const healthError = await checkCameraHealth();
        if (healthError) {
          throw new Error(healthError);
        }

        // No health issue detected, try showing preview anyway
        // The img onError handler will manage retries
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
  }, [cameraId, waitForStreamReady, checkCameraHealth, toast]);

  // Keep the ref updated with the latest function
  startPreviewRef.current = startPreviewWithRetry;

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
      const statusUrl = `/api/v1/cameras/${cameraId}/preview/status`;
      const response = await fetch(statusUrl, {
        signal: AbortSignal.timeout(1000),
      });

      if (response.ok) {
        const data = await response.json();
        const previewActive = data.state === "running";
        setIsPreviewActive(previewActive);
        if (previewActive) {
          setStreamKey(prev => prev + 1);
        }
        return previewActive;
      }

      setIsPreviewActive(false);
      return false;
    } catch {
      setIsPreviewActive(false);
      return false;
    }
  }, [cameraId]);

  // Check if preview is already running on mount, and auto-start if configured
  useEffect(() => {
    // If autoStart is enabled, immediately show the preview area and try to start
    // Don't wait for status check - it can hang during navigation
    if (autoStart && !autoStartAttempted) {
      setAutoStartAttempted(true);
      // Immediately set active to show the stream img element
      // The img onError will handle if stream isn't actually available
      setIsPreviewActive(true);
      setStreamKey(prev => prev + 1);

      // Also try to start in background (will succeed or return "already running")
      startPreviewRef.current?.(false);
    } else if (!autoStart) {
      // If not auto-starting, check status to see if we should display
      checkPreviewStatus();
    }
  }, [checkPreviewStatus, autoStart, autoStartAttempted]);

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

  // NOTE: We intentionally do NOT stop previews on component unmount.
  // Previews are a shared resource managed by the dashboard watchdog.
  // Stopping on unmount causes the dashboard feeds to disappear when
  // navigating between camera pages and home, since PreviewTab unmount
  // would stop the preview that the dashboard's LiveThumbnail needs.
  // The watchdog handles starting previews, and they run until:
  // 1. User explicitly clicks "Stop Preview"
  // 2. A capture/recording/timelapse operation needs the camera
  // 3. The camera is disabled

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
      const { error } = await stopPreview(cameraId);

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

  // Expose control methods via ref
  useImperativeHandle(ref, () => ({
    startPreview: handleStartPreview,
    stopPreview: handleStopPreview,
    isPreviewActive,
    isLoading,
  }), [isPreviewActive, isLoading]);

  // Determine display message for connecting state
  const connectingMessage = isConnecting
    ? (errorMessage || "Connecting to camera...")
    : (retryCount > 0 && retryCount <= RETRY_CONFIG.maxRetries)
      ? errorMessage
      : "";

  return (
    <div className={`preview-tab ${hideControls ? 'preview-tab--no-controls' : ''}`}>
      {/* Only show controls if not hidden */}
      {!hideControls && (
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
      )}

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
              <p>{hideControls ? "Preview not running" : "Preview not running. Click \"Start Preview\" to begin."}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
