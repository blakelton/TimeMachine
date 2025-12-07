/**
 * Home dashboard page with real-time stats and camera status
 */

import { useQuery } from "@tanstack/react-query";
import { wsClient } from "../lib/websocket";
import { useWebSocket } from "../hooks/useWebSocket";
import { SystemStats } from "../components/SystemStats";
import { CameraStatusCard } from "../components/CameraStatusCard";
import { apiClient } from "../api/client";
import "./HomePage.css";

export function HomePage() {
  // Connect to WebSocket on mount
  const wsState = useWebSocket(wsClient);

  // Fetch cameras list
  const { data: camerasData, isLoading, error } = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/cameras");
      if (response.error) {
        throw new Error("Failed to fetch cameras");
      }
      return response.data;
    },
  });

  const cameras = camerasData?.data || [];

  return (
    <div className="home-page">
      <div className="page-header">
        <h1>TimeMachine Dashboard</h1>
        <div className="ws-status">
          <span className={`ws-indicator ${wsState}`}></span>
          <span className="ws-label">
            {wsState === "connected" ? "Live Updates" : `WebSocket ${wsState}`}
          </span>
        </div>
      </div>

      {/* System Statistics */}
      <SystemStats />

      {/* Camera Status */}
      <div className="cameras-section">
        <h2>Camera Status</h2>
        {isLoading && <div className="loading">Loading cameras...</div>}
        {error && (
          <div className="error">
            Failed to load cameras. Please check your connection.
          </div>
        )}
        {cameras.length === 0 && !isLoading && !error && (
          <div className="empty-state">
            <p>No cameras configured.</p>
            <p>Add cameras in the Settings page to get started.</p>
          </div>
        )}
        {cameras.length > 0 && (
          <div className="cameras-grid">
            {cameras.map((camera) => (
              <CameraStatusCard key={camera.id} camera={camera} />
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="actions-grid">
          <button className="action-button">
            <span className="action-icon">📷</span>
            <span className="action-label">Capture Still</span>
          </button>
          <button className="action-button">
            <span className="action-icon">🎥</span>
            <span className="action-label">Start Recording</span>
          </button>
          <button className="action-button">
            <span className="action-icon">⏱️</span>
            <span className="action-label">Start Timelapse</span>
          </button>
          <button className="action-button">
            <span className="action-icon">⚙️</span>
            <span className="action-label">Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
