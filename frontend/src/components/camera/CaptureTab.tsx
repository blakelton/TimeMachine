/**
 * Capture tab - Still image capture
 */

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { captureImage } from "../../api";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import "./CaptureTab.css";

export interface CaptureTabProps {
  cameraId: number;
}

// Response type from capture endpoint
interface CaptureResponse {
  success: boolean;
  message: string;
  filepath?: string | null;
}

export function CaptureTab({ cameraId }: CaptureTabProps) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastCaptureUrl, setLastCaptureUrl] = useState<string | null>(null);
  const [lastCaptureTime, setLastCaptureTime] = useState<string | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();

  const handleCapture = async () => {
    setIsCapturing(true);

    try {
      const { data, error } = await captureImage(cameraId);

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to capture image";
        throw new Error(errorMessage);
      }

      if (data) {
        const response = data as CaptureResponse;
        // filepath is the path that can be served via nginx
        if (response.filepath) {
          // Convert filepath to URL (e.g., /var/lib/timemachine/... -> /media/...)
          const filename = response.filepath.split('/').pop();
          const imageUrl = `/media/stills/${filename}`;
          setLastCaptureUrl(imageUrl);
          setLastCaptureTime(new Date().toLocaleString());
        }
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
