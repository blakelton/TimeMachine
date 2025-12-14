/**
 * Camera action bar with Preview, Capture, and Start Observation buttons
 */

import { useState } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./CameraActionBar.css";

export interface CameraActionBarProps {
  cameraId: number;
  isPreviewActive: boolean;
  isObservationActive: boolean;
  onTogglePreview: () => void;
  onStartObservation: () => void;
}

export function CameraActionBar({
  cameraId,
  isPreviewActive,
  isObservationActive,
  onTogglePreview,
  onStartObservation,
}: CameraActionBarProps) {
  const [isCapturing, setIsCapturing] = useState(false);
  const toast = useToast();

  const handleCapture = async () => {
    setIsCapturing(true);

    try {
      const { data, error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/capture" as any,
        {
          params: { path: { camera_id: cameraId } },
          body: { quality: 95 }, // Default high quality
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
        toast.success("Image captured successfully");
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
    <div className="camera-action-bar">
      <Button
        variant={isPreviewActive ? "primary" : "secondary"}
        onClick={onTogglePreview}
        disabled={isObservationActive}
        className="camera-action-bar__button"
      >
        {isPreviewActive ? "Stop Preview" : "Preview"}
      </Button>

      <Button
        variant="secondary"
        onClick={handleCapture}
        disabled={isCapturing || isObservationActive}
        className="camera-action-bar__button"
      >
        {isCapturing ? "Capturing..." : "Capture"}
      </Button>

      <Button
        variant="primary"
        onClick={onStartObservation}
        disabled={isObservationActive}
        className="camera-action-bar__button camera-action-bar__button--observation"
      >
        Start Observation
      </Button>
    </div>
  );
}
