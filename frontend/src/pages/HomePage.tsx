/**
 * Home dashboard page with system stats and camera status
 *
 * Features:
 * - Live camera previews when idle (configurable in settings)
 * - Timelapse/recording progress when active
 * - System resource monitoring
 */

import { SystemStats } from "../components/SystemStats";
import { CameraPreviewCard } from "../components/CameraPreviewCard";
import { useCameraDashboard } from "../hooks/useCameraDashboard";
import { useDashboardSettings } from "../hooks/useDashboardSettings";
import "./HomePage.css";

export function HomePage() {
  // Fetch dashboard preview settings
  const { settings: previewSettings } = useDashboardSettings();

  // Fetch camera dashboard data with preview states
  // Pass settings to auto-start previews when enabled
  const { cameras, isLoading, isError } = useCameraDashboard({
    refetchInterval: 3000, // Poll every 3 seconds
    previewSettings,
  });

  return (
    <div className="home-page">
      <div className="page-header">
        <h1>📊 TimeMachine Dashboard</h1>
      </div>

      {/* System Statistics */}
      <SystemStats />

      {/* Camera Status */}
      <div className="cameras-section">
        <h2>📷 Cameras</h2>
        {isLoading && <div className="loading">Loading cameras...</div>}
        {isError && (
          <div className="error">
            Failed to load cameras. Please check your connection.
          </div>
        )}
        {cameras.length === 0 && !isLoading && !isError && (
          <div className="empty-state">
            <p>No cameras configured.</p>
            <p>Add cameras in the Settings page to get started.</p>
          </div>
        )}
        {cameras.length > 0 && (
          <div className="cameras-grid">
            {cameras.map((camera) => (
              <CameraPreviewCard key={camera.camera_id} camera={camera} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
