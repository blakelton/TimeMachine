/**
 * System settings page with sidebar navigation
 */

import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import "./SystemPage.css";

export function SystemPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect to cameras if on base /system path
  if (location.pathname === "/system" || location.pathname === "/system/") {
    navigate("/system/cameras", { replace: true });
  }

  return (
    <div className="system-page">
      {/* Sidebar navigation - always visible */}
      <aside className="settings-sidebar">
        <div className="sidebar-header">
          <h2>System Settings</h2>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/system/cameras"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-icon">📷</span>
            <span className="sidebar-label">Cameras</span>
          </NavLink>

          <NavLink
            to="/system/output"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-icon">💾</span>
            <span className="sidebar-label">Output Config</span>
          </NavLink>

          <NavLink
            to="/system/notifications"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-icon">🔔</span>
            <span className="sidebar-label">Notifications</span>
          </NavLink>

          <NavLink
            to="/system/environment"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-icon">🌡️</span>
            <span className="sidebar-label">Environment</span>
          </NavLink>
        </nav>
      </aside>

      {/* Main content area */}
      <main className="settings-content">
        <Outlet />
      </main>
    </div>
  );
}
