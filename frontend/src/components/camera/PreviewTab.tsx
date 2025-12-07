/**
 * Preview tab - Live MJPEG camera preview
 */

import { useState, useEffect, useRef } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./PreviewTab.css";

export interface PreviewTabProps {
  cameraId: number;
}

export function PreviewTab({ cameraId }: PreviewTabProps) {
  const [isPreviewActive, setIsPreviewActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const imgRef = useRef<HTMLImageElement>(null);
  const toast = useToast();

  // Check if preview is already running on mount
  useEffect(() => {
    checkPreviewStatus();
  }, [cameraId]);

  const checkPreviewStatus = async () => {
    try {
      // Try to load the preview stream to see if it's active
      const streamUrl = getStreamUrl();
      const response = await fetch(streamUrl, { method: "HEAD" });
      setIsPreviewActive(response.ok);
      setHasError(!response.ok);
    } catch (error) {
      setIsPreviewActive(false);
      setHasError(true);
    }
  };

  const getStreamUrl = () => {
    const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    return `${baseUrl}/api/v1/cameras/${cameraId}/preview/stream`;
  };

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
