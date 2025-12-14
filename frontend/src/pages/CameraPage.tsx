/**
 * Camera page with live preview and observation controls
 *
 * Layout:
 * - Header with camera name and status
 * - Live preview (or observation in progress view)
 * - Action bar: Preview, Capture, Start Observation
 */

import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { PreviewTab } from "../components/camera/PreviewTab";
import { CameraActionBar } from "../components/camera/CameraActionBar";
import { StartObservationModal } from "../components/camera/StartObservationModal";
import { ObservationInProgress } from "../components/camera/ObservationInProgress";
import "./CameraPage.css";

interface ActiveObservation {
  id: number;
  observation_type: string;
  status: string;
}

export function CameraPage() {
  const { cameraId } = useParams<{ cameraId: string }>();

  const cameraIdNum = parseInt(cameraId || "0");

  // Local state for preview
  const [isPreviewActive, setIsPreviewActive] = useState(true);
  const [showObservationModal, setShowObservationModal] = useState(false);

  // Fetch camera details
  const { data: camera, isLoading } = useQuery({
    queryKey: ["camera", cameraIdNum],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/cameras/{camera_id}",
        {
          params: { path: { camera_id: cameraIdNum } },
        }
      );
      if (error) throw error;
      return data;
    },
    enabled: !isNaN(cameraIdNum) && cameraIdNum > 0,
  });

  // Fetch active observation for this camera
  const { data: activeObsData, refetch: refetchActiveObs } = useQuery({
    queryKey: ["activeObservation", cameraIdNum],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/api/v1/observations/camera/{camera_id}/active" as any,
        {
          params: { path: { camera_id: cameraIdNum } },
        }
      );
      if (error) throw error;
      return data as { has_active: boolean; observation: ActiveObservation | null };
    },
    enabled: !isNaN(cameraIdNum) && cameraIdNum > 0,
    refetchInterval: 3000,
  });

  const activeObservation = activeObsData?.observation || null;
  const isObservationActive = activeObsData?.has_active === true;

  if (isNaN(cameraIdNum) || cameraIdNum <= 0) {
    return (
      <div className="camera-page">
        <div className="camera-page__error">Invalid camera ID</div>
      </div>
    );
  }

  const handleTogglePreview = () => {
    setIsPreviewActive(!isPreviewActive);
  };

  const handleStartObservation = () => {
    setShowObservationModal(true);
  };

  const handleObservationStarted = () => {
    refetchActiveObs();
  };

  const handleObservationStopped = () => {
    refetchActiveObs();
  };

  return (
    <div className="camera-page">
      {/* Header */}
      <div className="camera-page__header">
        <h1 className="camera-page__title">
          {isLoading ? "Loading..." : camera?.name || `Camera ${cameraId}`}
        </h1>
        {camera && (
          <div className="camera-page__info">
            <span className="camera-page__type">
              {camera.camera_type?.toUpperCase()}
            </span>
            <span className="camera-page__status">
              {camera.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
        )}
      </div>

      {/* Main content area */}
      {isObservationActive && activeObservation ? (
        // Show Observation In Progress
        <ObservationInProgress
          observationId={activeObservation.id}
          cameraId={cameraIdNum}
          onStopped={handleObservationStopped}
        />
      ) : (
        // Show Preview and Action Bar
        <>
          {/* Live Preview */}
          <div className="camera-page__preview">
            {isPreviewActive ? (
              <PreviewTab cameraId={cameraIdNum} autoStart />
            ) : (
              <div className="camera-page__preview-placeholder">
                <span>Preview Stopped</span>
                <p>Click "Preview" to start the camera preview</p>
              </div>
            )}
          </div>

          {/* Action Bar */}
          <CameraActionBar
            cameraId={cameraIdNum}
            isPreviewActive={isPreviewActive}
            isObservationActive={isObservationActive}
            onTogglePreview={handleTogglePreview}
            onStartObservation={handleStartObservation}
          />
        </>
      )}

      {/* Start Observation Modal */}
      <StartObservationModal
        cameraId={cameraIdNum}
        isOpen={showObservationModal}
        onClose={() => setShowObservationModal(false)}
        onStarted={handleObservationStarted}
      />
    </div>
  );
}
