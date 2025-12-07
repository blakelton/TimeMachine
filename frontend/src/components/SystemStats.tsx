/**
 * Real-time system statistics display component
 */

import { useState, useCallback } from "react";
import { wsClient } from "../lib/websocket";
import { useWebSocketMessage } from "../hooks/useWebSocket";
import type { WSStatsUpdate } from "../types/websocket";
import "./SystemStats.css";

interface SystemStatsData {
  cpu_percent: number;
  memory_percent: number;
  disk_free_gb: number;
  temperature_celsius: number | null;
  timestamp: string;
}

export function SystemStats() {
  const [stats, setStats] = useState<SystemStatsData | null>(null);

  // Subscribe to stats updates from WebSocket
  const handleStatsUpdate = useCallback((message: WSStatsUpdate) => {
    setStats({
      cpu_percent: message.cpu_percent,
      memory_percent: message.memory_percent,
      disk_free_gb: message.disk_free_gb,
      temperature_celsius: message.temperature_celsius,
      timestamp: message.timestamp,
    });
  }, []);

  useWebSocketMessage(wsClient, "stats_update", handleStatsUpdate);

  if (!stats) {
    return (
      <div className="system-stats loading">
        <div className="stats-header">
          <h2>System Statistics</h2>
          <span className="connection-status">Connecting...</span>
        </div>
      </div>
    );
  }

  const getStatusClass = (percent: number, type: "cpu" | "memory" | "disk") => {
    if (type === "disk") {
      // For disk, free space below thresholds is concerning
      const usedPercent = 100 - (stats.disk_free_gb / 32) * 100; // Assume 32GB typical
      if (usedPercent > 90) return "critical";
      if (usedPercent > 80) return "warning";
      return "ok";
    }

    if (percent > 90) return "critical";
    if (percent > 75) return "warning";
    return "ok";
  };

  const getTempStatus = (temp: number | null) => {
    if (temp === null) return "unknown";
    if (temp > 80) return "critical";
    if (temp > 70) return "warning";
    return "ok";
  };

  return (
    <div className="system-stats">
      <div className="stats-header">
        <h2>System Statistics</h2>
        <span className="connection-status connected">Live</span>
      </div>

      <div className="stats-grid">
        {/* CPU Usage */}
        <div className={`stat-card ${getStatusClass(stats.cpu_percent, "cpu")}`}>
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-label">CPU Usage</div>
            <div className="stat-value">{stats.cpu_percent.toFixed(1)}%</div>
            <div className="stat-bar">
              <div
                className="stat-bar-fill"
                style={{ width: `${Math.min(stats.cpu_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Memory Usage */}
        <div className={`stat-card ${getStatusClass(stats.memory_percent, "memory")}`}>
          <div className="stat-icon">💾</div>
          <div className="stat-content">
            <div className="stat-label">Memory Usage</div>
            <div className="stat-value">{stats.memory_percent.toFixed(1)}%</div>
            <div className="stat-bar">
              <div
                className="stat-bar-fill"
                style={{ width: `${Math.min(stats.memory_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Disk Space */}
        <div className={`stat-card ${getStatusClass(stats.disk_free_gb, "disk")}`}>
          <div className="stat-icon">💿</div>
          <div className="stat-content">
            <div className="stat-label">Disk Free</div>
            <div className="stat-value">{stats.disk_free_gb.toFixed(1)} GB</div>
          </div>
        </div>

        {/* Temperature */}
        <div
          className={`stat-card ${
            stats.temperature_celsius !== null
              ? getTempStatus(stats.temperature_celsius)
              : ""
          }`}
        >
          <div className="stat-icon">🌡️</div>
          <div className="stat-content">
            <div className="stat-label">CPU Temperature</div>
            <div className="stat-value">
              {stats.temperature_celsius !== null
                ? `${stats.temperature_celsius.toFixed(1)}°C`
                : "N/A"}
            </div>
          </div>
        </div>
      </div>

      <div className="stats-footer">
        <span className="last-update">
          Last update: {new Date(stats.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}
