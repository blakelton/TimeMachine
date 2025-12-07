/**
 * Main layout component with responsive navigation
 */

import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./Layout.css";

export function Layout() {
  const location = useLocation();
  const { logout, isAuthenticated } = useAuth();

  const isActive = (path: string) => location.pathname === path;

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
          <Link
            to="/system"
            className={isActive("/system") ? "nav-link active" : "nav-link"}
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
