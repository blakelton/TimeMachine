/**
 * Live MJPEG thumbnail component with graceful error handling.
 *
 * Displays a live camera feed from an MJPEG stream URL.
 * Handles connection failures gracefully without breaking the UI.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import "./LiveThumbnail.css";

interface LiveThumbnailProps {
  /**
   * URL to the MJPEG stream
   */
  streamUrl: string;
  /**
   * Alt text for the image
   */
  alt: string;
  /**
   * Optional CSS class name
   */
  className?: string;
  /**
   * Placeholder to show when stream fails or is loading
   */
  fallbackIcon?: string;
  /**
   * Maximum retries before showing permanent error.
   * Default is 5 to handle slow-starting streams.
   */
  maxRetries?: number;
  /**
   * Delay between retries in ms.
   * Default is 1500ms for faster recovery.
   */
  retryDelay?: number;
  /**
   * Optional key to force component reset.
   * Change this value to reset the error state and retry loading.
   */
  refreshKey?: string | number;
}

type StreamState = "loading" | "connected" | "error" | "retrying";

/**
 * LiveThumbnail displays a live MJPEG camera feed with error recovery.
 *
 * Features:
 * - Automatic retry on connection failure
 * - Graceful degradation to placeholder on error
 * - Memory-efficient cleanup on unmount
 *
 * @example
 * ```tsx
 * <LiveThumbnail
 *   streamUrl="http://localhost:8081"
 *   alt="Camera 1 preview"
 *   fallbackIcon="📷"
 * />
 * ```
 */
export function LiveThumbnail({
  streamUrl,
  alt,
  className = "",
  fallbackIcon = "📷",
  maxRetries = 5,
  retryDelay = 1500,
  refreshKey,
}: LiveThumbnailProps) {

  const [state, setState] = useState<StreamState>("loading");
  const [retryCount, setRetryCount] = useState(0);
  // Controls whether img element is rendered - toggling this forces complete DOM removal/recreation
  const [imgMounted, setImgMounted] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const retryTimeoutRef = useRef<number | null>(null);
  const prevUrlRef = useRef<string>(streamUrl);
  const prevRefreshKeyRef = useRef<string | number | undefined>(refreshKey);
  const mountedRef = useRef(true);
  // Unique timestamp per mount - ensures fresh HTTP connection, prevents stale connection reuse
  const mountTimestampRef = useRef<number>(Date.now());


  // Reset state on mount, URL change, or refreshKey change
  useEffect(() => {
    // Reset state on mount - critical for navigation recovery
    mountedRef.current = true;
    setState("loading");
    setRetryCount(0);

    // Generate fresh timestamp for this mount
    mountTimestampRef.current = Date.now();

    // Clear any stale timeout from previous mount
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    // Start with img unmounted, then mount after a delay
    // The delay gives browser time to fully close previous MJPEG connections
    // (Browser has ~6 connection limit per domain; MJPEG streams are persistent)
    setImgMounted(false);
    const mountDelay = window.setTimeout(() => {
      if (mountedRef.current) {
        setImgMounted(true);
      }
    }, 500); // 500ms delay to ensure old connections are closed

    return () => {
      mountedRef.current = false;
      window.clearTimeout(mountDelay);
      // Clear retry timeout
      if (retryTimeoutRef.current !== null) {
        window.clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      // Force-abort the img connection by clearing src
      if (imgRef.current) {
        imgRef.current.src = "";
      }
      setImgMounted(false);

      // Call window.stop() to forcefully abort ALL pending network requests
      // This mimics clicking the browser Stop button which reliably fixes the issue
      window.stop();
    };
  }, [streamUrl, refreshKey]); // Re-run when URL or refreshKey changes to reset state

  // Reset state when URL or refreshKey changes using ref comparison
  if (prevUrlRef.current !== streamUrl || prevRefreshKeyRef.current !== refreshKey) {
    prevUrlRef.current = streamUrl;
    prevRefreshKeyRef.current = refreshKey;
    // Clear existing timeout on change
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    setState("loading");
    setRetryCount(0);
  }

  const handleLoad = useCallback(() => {
    setState("connected");
    setRetryCount(0);
  }, []);

  const handleError = useCallback(() => {
    // Don't process errors if component unmounted
    if (!mountedRef.current) return;

    // Clear any existing timeout before setting a new one
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current);
    }

    if (retryCount < maxRetries) {
      setState("retrying");
      retryTimeoutRef.current = window.setTimeout(() => {
        // Check mounted before updating state
        if (!mountedRef.current) return;
        setRetryCount((prev) => prev + 1);
        // Force image reload by appending fresh timestamp
        if (imgRef.current) {
          const separator = streamUrl.includes("?") ? "&" : "?";
          imgRef.current.src = `${streamUrl}${separator}_t=${Date.now()}`;
        }
        setState("loading");
      }, retryDelay);
    } else {
      setState("error");
    }
  }, [retryCount, maxRetries, retryDelay, streamUrl]);

  const containerClass = `live-thumbnail ${className} ${state}`.trim();

  // Show placeholder for error/retrying states
  if (state === "error") {
    return (
      <div
        className={containerClass}
        role="img"
        aria-label={`${alt} - Stream unavailable`}
        title={`${alt} - Stream unavailable`}
      >
        <div className="thumbnail-placeholder">
          <span className="placeholder-icon" aria-hidden="true">{fallbackIcon}</span>
          <span className="placeholder-text">No signal</span>
        </div>
      </div>
    );
  }

  return (
    <div className={containerClass}>
      {(state === "loading" || state === "retrying" || !imgMounted) && (
        <div className="thumbnail-loading" aria-hidden="true">
          <span className="loading-icon">{fallbackIcon}</span>
          {state === "retrying" && (
            <span className="retry-indicator">
              Retry {retryCount + 1}/{maxRetries}
            </span>
          )}
        </div>
      )}
      {imgMounted && (
        <img
          ref={imgRef}
          src={`${streamUrl}${streamUrl.includes("?") ? "&" : "?"}_t=${mountTimestampRef.current}`}
          alt={state === "connected" ? alt : `${alt} (loading)`}
          className="thumbnail-image"
          onLoad={handleLoad}
          onError={handleError}
          style={{ opacity: state === "connected" ? 1 : 0 }}
        />
      )}
    </div>
  );
}
