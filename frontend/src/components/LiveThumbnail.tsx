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
   * Maximum retries before showing permanent error
   */
  maxRetries?: number;
  /**
   * Delay between retries in ms
   */
  retryDelay?: number;
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
  maxRetries = 3,
  retryDelay = 2000,
}: LiveThumbnailProps) {
  const [state, setState] = useState<StreamState>("loading");
  const [retryCount, setRetryCount] = useState(0);
  const imgRef = useRef<HTMLImageElement>(null);
  const retryTimeoutRef = useRef<number | null>(null);
  const prevUrlRef = useRef<string>(streamUrl);

  // Clear any pending retry and stop MJPEG stream on unmount
  useEffect(() => {
    return () => {
      // Clear retry timeout
      if (retryTimeoutRef.current !== null) {
        window.clearTimeout(retryTimeoutRef.current);
      }
      // Stop MJPEG stream by clearing the src - critical for memory management
      // MJPEG streams keep connections open until explicitly stopped
      if (imgRef.current) {
        imgRef.current.src = "";
      }
    };
  }, []);

  // Reset state when URL changes using ref comparison (avoids setState in useEffect)
  if (prevUrlRef.current !== streamUrl) {
    prevUrlRef.current = streamUrl;
    // Clear existing timeout on URL change
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
    // Clear any existing timeout before setting a new one
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current);
    }

    if (retryCount < maxRetries) {
      setState("retrying");
      retryTimeoutRef.current = window.setTimeout(() => {
        setRetryCount((prev) => prev + 1);
        // Force image reload by appending timestamp
        if (imgRef.current) {
          const separator = streamUrl.includes("?") ? "&" : "?";
          imgRef.current.src = `${streamUrl}${separator}_retry=${Date.now()}`;
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
      {(state === "loading" || state === "retrying") && (
        <div className="thumbnail-loading" aria-hidden="true">
          <span className="loading-icon">{fallbackIcon}</span>
          {state === "retrying" && (
            <span className="retry-indicator">
              Retry {retryCount + 1}/{maxRetries}
            </span>
          )}
        </div>
      )}
      <img
        ref={imgRef}
        src={streamUrl}
        alt={state === "connected" ? alt : `${alt} (loading)`}
        className="thumbnail-image"
        onLoad={handleLoad}
        onError={handleError}
        style={{ opacity: state === "connected" ? 1 : 0 }}
      />
    </div>
  );
}
