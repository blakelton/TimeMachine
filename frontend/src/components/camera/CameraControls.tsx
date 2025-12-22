/**
 * Camera controls - consolidated action buttons for camera page
 *
 * Combines preview start/stop, capture, and observation controls
 * into a single compact row.
 */

import { useState } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import type { PreviewTabHandle } from "./PreviewTab";
import "./CameraControls.css";

export interface CameraControlsProps {
  cameraId: number;
  previewRef: React.RefObject<PreviewTabHandle | null>;
  onStartObservation: () => void;
}

export function CameraControls({
  cameraId,
  previewRef,
  onStartObservation,
}: CameraControlsProps) {
  const [isCapturing, setIsCapturing] = useState(false);
  const toast = useToast();

  const isPreviewActive = previewRef.current?.isPreviewActive ?? false;
  const isPreviewLoading = previewRef.current?.isLoading ?? false;

  const handleTogglePreview = () => {
    if (isPreviewActive) {
      previewRef.current?.stopPreview();
    } else {
      previewRef.current?.startPreview();
    }
  };

  const handleCapture = async () => {
    setIsCapturing(true);

    try {
      const { data, error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/capture" as any,
        {
          params: { path: { camera_id: cameraId } },
          body: { quality: 95 },
        }
      );

      if (error) {
        const errorMessage =
          typeof error.detail === "string"
            ? error.detail
            : "Failed to capture image";
        throw new Error(errorMessage);
      }

      if (data) {
        toast.success("Image captured");
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to capture image";
      toast.error(message);
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <div className="camera-controls">
      <Button
        variant={isPreviewActive ? "secondary" : "primary"}
        onClick={handleTogglePreview}
        disabled={isPreviewLoading}
        className="camera-controls__btn"
      >
        {isPreviewLoading
          ? "..."
          : isPreviewActive
          ? "Stop"
          : "Preview"}
      </Button>

      <Button
        variant="secondary"
        onClick={handleCapture}
        disabled={isCapturing}
        className="camera-controls__btn"
      >
        {isCapturing ? "..." : "Capture"}
      </Button>

      <Button
        variant="primary"
        onClick={onStartObservation}
        className="camera-controls__btn camera-controls__btn--observe"
      >
        Observe
      </Button>
    </div>
  );
}
