/**
 * System settings page with sidebar navigation
 */

import { useState } from "react";
import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import "./SystemPage.css";

export function SystemPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect to cameras if on base /system path
  if (location.pathname === "/system" || location.pathname === "/system/") {
    navigate("/system/cameras", { replace: true });
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  return (
    <div className="system-page">
      {/* Mobile hamburger menu */}
      <button
        className="sidebar-toggle"
        onClick={toggleSidebar}
        aria-label="Toggle settings menu"
        aria-expanded={sidebarOpen}
      >
        <span className="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </span>
      </button>

      {/* Sidebar navigation */}
      <aside className={`settings-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h2>System Settings</h2>
          <button
            className="sidebar-close"
            onClick={closeSidebar}
            aria-label="Close settings menu"
          >
            ✕
          </button>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/system/cameras"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
            onClick={closeSidebar}
          >
            <span className="sidebar-icon">📷</span>
            <span className="sidebar-label">Cameras</span>
          </NavLink>

          <NavLink
            to="/system/output"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
            onClick={closeSidebar}
          >
            <span className="sidebar-icon">💾</span>
            <span className="sidebar-label">Output Config</span>
          </NavLink>

          <NavLink
            to="/system/notifications"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
            onClick={closeSidebar}
          >
            <span className="sidebar-icon">🔔</span>
            <span className="sidebar-label">Notifications</span>
          </NavLink>

          <NavLink
            to="/system/temperature"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
            onClick={closeSidebar}
          >
            <span className="sidebar-icon">🌡️</span>
            <span className="sidebar-label">Temperature</span>
          </NavLink>
        </nav>
      </aside>

      {/* Backdrop for mobile */}
      {sidebarOpen && (
        <div className="sidebar-backdrop" onClick={closeSidebar}></div>
      )}

      {/* Main content area */}
      <main className="settings-content">
        <Outlet />
      </main>
    </div>
  );
}
