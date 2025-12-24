/**
 * Real-time system statistics display component
 *
 * Uses HTTP polling for reliable stats updates.
 * Falls back gracefully if the API is unavailable.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import "./SystemStats.css";

interface SystemStatsData {
  cpu_percent: number;
  memory_percent: number;
  memory_available_mb: number;
  disk_free_gb: number;
  disk_percent_used: number;
  temperature_celsius: number | null;
  timestamp: string;
}

export function SystemStats() {
  // Poll the health/stats endpoint every 3 seconds
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["systemStats"],
    queryFn: async (): Promise<SystemStatsData> => {
      const { data, error } = await apiClient.GET("/api/v1/health/stats");
      if (error || !data) {
        throw new Error("Failed to fetch system stats");
      }
      // Extract from wrapped response
      const statsData = (data as any).data;
      return {
        cpu_percent: statsData.cpu_percent,
        memory_percent: statsData.memory.percent,
        memory_available_mb: statsData.memory.available_mb,
        disk_free_gb: statsData.disk.free_gb,
        disk_percent_used: statsData.disk.percent_used,
        temperature_celsius: statsData.temperature_celsius,
        timestamp: statsData.timestamp,
      };
    },
    refetchInterval: 5000, // Poll every 5 seconds (reduced from 3s for performance)
    retry: 2,
    staleTime: 4000, // Consider data fresh for 4 seconds
  });

  if (isLoading) {
    return (
      <div className="system-stats loading">
        <div className="stats-header">
          <h2>System Statistics</h2>
          <span className="connection-status">Loading...</span>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="system-stats error">
        <div className="stats-header">
          <h2>System Statistics</h2>
          <span className="connection-status error">Unavailable</span>
        </div>
        <p className="stats-error-message">
          Unable to load system statistics. Check backend connection.
        </p>
      </div>
    );
  }

  const getStatusClass = (percent: number, type: "cpu" | "memory" | "disk") => {
    if (type === "disk") {
      // For disk, higher percent_used is concerning
      if (percent > 90) return "critical";
      if (percent > 80) return "warning";
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
            <div className="stat-detail">{stats.memory_available_mb.toFixed(0)} MB free</div>
          </div>
        </div>

        {/* Disk Space */}
        <div className={`stat-card ${getStatusClass(stats.disk_percent_used, "disk")}`}>
          <div className="stat-icon">💿</div>
          <div className="stat-content">
            <div className="stat-label">Disk Free</div>
            <div className="stat-value">{stats.disk_free_gb.toFixed(1)} GB</div>
            <div className="stat-bar">
              <div
                className="stat-bar-fill"
                style={{ width: `${Math.min(stats.disk_percent_used, 100)}%` }}
              />
            </div>
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
