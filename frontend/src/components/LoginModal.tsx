/**
 * Login modal for HTTP Basic Auth
 */

import { useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";
import "./LoginModal.css";

export function LoginModal() {
  const { isAuthenticated, authRequired, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const success = await login(username, password);
    setLoading(false);

    if (!success) {
      setError("Invalid username or password");
      setPassword("");
    }
  };

  // Don't show modal if authenticated or if auth is not required
  if (isAuthenticated || authRequired === false) {
    return null;
  }

  // Show loading state while checking auth status
  if (authRequired === null) {
    return null; // Or could show a loading spinner
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>TimeMachine Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
              autoComplete="current-password"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
}
