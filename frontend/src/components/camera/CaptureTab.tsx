/**
 * Capture tab - Still image capture with quality settings
 */

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { FormField } from "../FormField";
import { useToast } from "../../contexts/ToastContext";
import "./CaptureTab.css";

export interface CaptureTabProps {
  cameraId: number;
}

type QualityLevel = "low" | "medium" | "high" | "max";

export function CaptureTab({ cameraId }: CaptureTabProps) {
  const [quality, setQuality] = useState<QualityLevel>("high");
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastCaptureUrl, setLastCaptureUrl] = useState<string | null>(null);
  const [lastCaptureTime, setLastCaptureTime] = useState<string | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();

  const qualityValues: Record<QualityLevel, number> = {
    low: 50,
    medium: 75,
    high: 90,
    max: 100,
  };

  const handleCapture = async () => {
    setIsCapturing(true);

    try {
      const { data, error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/capture" as any,
        {
          params: { path: { camera_id: cameraId } },
          body: { quality: qualityValues[quality] },
        }
      );

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to capture image";
        throw new Error(errorMessage);
      }

      if (data) {
        // file_url is already an absolute path served by nginx (e.g., /media/stills/...)
        const imageUrl = (data as any).file_url;
        setLastCaptureUrl(imageUrl);
        setLastCaptureTime(new Date((data as any).timestamp).toLocaleString());
        toast.success("Image captured successfully");
        // Invalidate observations list so new capture appears immediately
        queryClient.invalidateQueries({ queryKey: ["observations"] });
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to capture image";
      toast.error(message);
    } finally {
      setIsCapturing(false);
    }
  };

  const handleDownload = () => {
    if (lastCaptureUrl) {
      const link = document.createElement("a");
      link.href = lastCaptureUrl;
      link.download = `capture_${Date.now()}.jpg`;
      link.click();
    }
  };

  return (
    <div className="capture-tab">
      <div className="capture-tab__controls">
        <FormField
          label="Quality"
          id="quality-select"
          element="select"
          value={quality}
          onChange={(e) => setQuality(e.target.value as QualityLevel)}
          disabled={isCapturing}
        >
          <option value="low">Low (50%)</option>
          <option value="medium">Medium (75%)</option>
          <option value="high">High (90%)</option>
          <option value="max">Maximum (100%)</option>
        </FormField>

        <Button
          variant="primary"
          onClick={handleCapture}
          disabled={isCapturing}
          className="capture-tab__capture-button"
        >
          {isCapturing ? "Capturing..." : "Capture Image"}
        </Button>
      </div>

      <div className="capture-tab__preview">
        {lastCaptureUrl ? (
          <div className="capture-tab__image-container">
            <img
              src={lastCaptureUrl}
              alt="Last captured image"
              className="capture-tab__image"
            />
            <div className="capture-tab__image-info">
              <span className="capture-tab__timestamp">
                Captured: {lastCaptureTime}
              </span>
              <Button
                variant="secondary"
                onClick={handleDownload}
              >
                Download
              </Button>
            </div>
          </div>
        ) : (
          <div className="capture-tab__placeholder">
            <p>No image captured yet</p>
            <p className="capture-tab__placeholder-hint">
              Click "Capture Image" to take a photo
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
