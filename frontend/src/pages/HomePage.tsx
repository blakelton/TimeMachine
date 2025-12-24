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
  // Use 5 second interval to reduce CPU/memory pressure on Pi
  const { cameras, isLoading, isError } = useCameraDashboard({
    refetchInterval: 5000, // Poll every 5 seconds (reduced from 3s)
    previewSettings,
  });

  return (
    <div className="home-page">
      <div className="page-header">
        <h1>📊 TimeMachine Dashboard</h1>
      </div>

      {/* Camera Status - Primary content, shown first */}
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

      {/* System Statistics - Bottom row */}
      <SystemStats />
    </div>
  );
}
