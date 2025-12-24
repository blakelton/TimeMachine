/**
 * Camera page with live preview and observation controls
 *
 * Layout (optimized for 800x480 touchscreen):
 * - Header row: Title + badges (left), controls (right)
 * - Full-size preview area below
 */

import { useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { PreviewTab } from "../components/camera/PreviewTab";
import type { PreviewTabHandle } from "../components/camera/PreviewTab";
import { CameraControls } from "../components/camera/CameraControls";
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
  const previewRef = useRef<PreviewTabHandle>(null);

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
    refetchInterval: 5000, // Reduced from 3s for performance
    staleTime: 4000,
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
      {/* Header with title, badges, and controls */}
      <div className="camera-page__header">
        <div className="camera-page__title-section">
          <h1 className="camera-page__title">
            {isLoading ? "Loading..." : camera?.name || `Camera ${cameraId}`}
          </h1>
          {camera && (
            <div className="camera-page__badges">
              <span className="camera-page__badge camera-page__badge--type">
                {camera.camera_type?.toUpperCase()}
              </span>
              <span className={`camera-page__badge camera-page__badge--status ${camera.enabled ? 'camera-page__badge--enabled' : 'camera-page__badge--disabled'}`}>
                {camera.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
          )}
        </div>

        {/* Controls - only show when no observation active */}
        {!isObservationActive && (
          <CameraControls
            cameraId={cameraIdNum}
            previewRef={previewRef}
            onStartObservation={handleStartObservation}
          />
        )}
      </div>

      {/* Main content area - maximized preview */}
      {isObservationActive && activeObservation ? (
        <ObservationInProgress
          observationId={activeObservation.id}
          cameraId={cameraIdNum}
          onStopped={handleObservationStopped}
        />
      ) : (
        <div className="camera-page__preview">
          <PreviewTab ref={previewRef} cameraId={cameraIdNum} autoStart hideControls />
        </div>
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
