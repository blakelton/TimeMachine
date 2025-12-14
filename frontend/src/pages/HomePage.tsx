/**
 * Home dashboard page with system stats and camera status
 */

import { useQuery } from "@tanstack/react-query";
import { SystemStats } from "../components/SystemStats";
import { CameraStatusCard } from "../components/CameraStatusCard";
import { apiClient } from "../api/client";
import "./HomePage.css";

export function HomePage() {
  // Fetch cameras list
  const {
    data: camerasData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/cameras");
      if (response.error) {
        throw new Error("Failed to fetch cameras");
      }
      return response.data;
    },
  });

  const cameras = (camerasData as any)?.cameras || [];

  return (
    <div className="home-page">
      <div className="page-header">
        <h1>TimeMachine Dashboard</h1>
      </div>

      {/* System Statistics */}
      <SystemStats />

      {/* Camera Status */}
      <div className="cameras-section">
        <h2>Cameras</h2>
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
            {cameras.map((camera: any) => (
              <CameraStatusCard key={camera.id} camera={camera} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
