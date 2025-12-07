/**
 * Camera page with tab navigation
 */

import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { PreviewTab } from "../components/camera/PreviewTab";
import { CaptureTab } from "../components/camera/CaptureTab";
import { RecordTab } from "../components/camera/RecordTab";
import { TimelapseTab } from "../components/camera/TimelapseTab";
import "./CameraPage.css";

type TabType = "preview" | "capture" | "record" | "timelapse";

const TABS: { id: TabType; label: string }[] = [
  { id: "preview", label: "Preview" },
  { id: "capture", label: "Capture" },
  { id: "record", label: "Record" },
  { id: "timelapse", label: "Timelapse" },
];

export function CameraPage() {
  const { cameraId, tab = "preview" } = useParams<{
    cameraId: string;
    tab?: TabType;
  }>();
  const navigate = useNavigate();

  const cameraIdNum = parseInt(cameraId || "0");

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

  if (isNaN(cameraIdNum) || cameraIdNum <= 0) {
    return (
      <div className="camera-page">
        <div className="camera-page__error">Invalid camera ID</div>
      </div>
    );
  }

  const currentTab = (tab as TabType) || "preview";

  const handleTabChange = (newTab: TabType) => {
    navigate(`/camera/${cameraId}/${newTab}`);
  };

  return (
    <div className="camera-page">
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

      <div className="camera-page__tabs">
        <div className="camera-page__tab-nav">
          {TABS.map((tabItem) => (
            <button
              key={tabItem.id}
              className={`camera-page__tab-button ${
                currentTab === tabItem.id
                  ? "camera-page__tab-button--active"
                  : ""
              }`}
              onClick={() => handleTabChange(tabItem.id)}
            >
              {tabItem.label}
            </button>
          ))}
        </div>

        <div className="camera-page__tab-content">
          {currentTab === "preview" && <PreviewTab cameraId={cameraIdNum} />}
          {currentTab === "capture" && <CaptureTab cameraId={cameraIdNum} />}
          {currentTab === "record" && <RecordTab cameraId={cameraIdNum} />}
          {currentTab === "timelapse" && (
            <TimelapseTab cameraId={cameraIdNum} />
          )}
        </div>
      </div>
    </div>
  );
}
