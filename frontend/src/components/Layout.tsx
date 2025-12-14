/**
 * Main layout component with responsive navigation
 */

import { Link, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import "./Layout.css";

export function Layout() {
  const location = useLocation();
  const { logout, isAuthenticated } = useAuth();

  // Fetch cameras for dynamic navigation tabs
  const { data: camerasData } = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/cameras");
      if (response.error) {
        throw new Error("Failed to fetch cameras");
      }
      return response.data;
    },
    staleTime: 30000, // Cache for 30 seconds
    refetchOnWindowFocus: true,
  });

  const cameras = camerasData?.cameras || [];
  const enabledCameras = cameras.filter((cam) => cam.enabled);

  const isActive = (path: string) => location.pathname === path;
  const isCameraActive = (cameraId: number) =>
    location.pathname.startsWith(`/camera/${cameraId}`);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>TimeMachine</h1>
        <nav className="main-nav">
          <Link
            to="/"
            className={isActive("/") ? "nav-link active" : "nav-link"}
          >
            Home
          </Link>

          {/* Dynamic camera tabs */}
          {enabledCameras.length > 0 && (
            <>
              <span className="nav-separator" aria-hidden="true">|</span>
              {enabledCameras.map((camera) => (
                <Link
                  key={camera.id}
                  to={`/camera/${camera.id}/preview`}
                  className={isCameraActive(camera.id) ? "nav-link active" : "nav-link"}
                  title={`${camera.name} (${camera.camera_type.toUpperCase()})`}
                >
                  {camera.name}
                </Link>
              ))}
            </>
          )}

          <span className="nav-separator" aria-hidden="true">|</span>
          <Link
            to="/files"
            className={isActive("/files") ? "nav-link active" : "nav-link"}
          >
            Files
          </Link>
          <Link
            to="/system"
            className={location.pathname.startsWith("/system") ? "nav-link active" : "nav-link"}
          >
            System
          </Link>
        </nav>
        {isAuthenticated && (
          <button onClick={logout} className="logout-button">
            Logout
          </button>
        )}
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>TimeMachine Observation Chamber Control System</p>
      </footer>
    </div>
  );
}
