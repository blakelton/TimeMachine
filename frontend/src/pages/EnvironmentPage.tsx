/**
 * Environment monitoring page with real-time sensor readings and graphs
 */

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "../api/client";
import { SensorCard } from "../components/environment/SensorCard";
import type { components } from "../types/api";
import "./EnvironmentPage.css";

type DeviceCurrentReading = components["schemas"]["DeviceCurrentReading"];

export function EnvironmentPage() {
  // Fetch current readings from all devices - refresh every 5 seconds
  const { data, isLoading, isError } = useQuery({
    queryKey: ["environment-readings-current"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/environment/readings/current");
      if (response.error) {
        throw new Error("Failed to fetch environment readings");
      }
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds for real-time updates
    staleTime: 3000,
  });

  const readings = data?.readings || [];
  const enabledReadings = readings.filter((r: DeviceCurrentReading) => r.enabled);

  return (
    <div className="environment-page">
      <div className="page-header">
        <h1>Environment Monitoring</h1>
        <p className="page-description">
          Real-time environmental sensor readings from configured devices
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="page-loading">
          <div className="loading-spinner"></div>
          <p>Loading sensor data...</p>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="page-error">
          <p>Failed to load sensor data. Please try again.</p>
        </div>
      )}

      {/* No devices configured */}
      {!isLoading && !isError && readings.length === 0 && (
        <div className="page-empty">
          <div className="empty-icon">🌡️</div>
          <h2>No Sensors Configured</h2>
          <p>
            Configure environment sensors to monitor temperature, humidity, and other conditions.
          </p>
          <Link to="/system/environment" className="btn btn-primary">
            Configure Sensors
          </Link>
        </div>
      )}

      {/* No enabled devices */}
      {!isLoading && !isError && readings.length > 0 && enabledReadings.length === 0 && (
        <div className="page-empty">
          <div className="empty-icon">🔌</div>
          <h2>All Sensors Disabled</h2>
          <p>
            You have {readings.length} sensor(s) configured but none are enabled.
          </p>
          <Link to="/system/environment" className="btn btn-primary">
            Enable Sensors
          </Link>
        </div>
      )}

      {/* Sensor cards grid */}
      {!isLoading && !isError && enabledReadings.length > 0 && (
        <div className="sensors-grid">
          {enabledReadings.map((reading: DeviceCurrentReading) => (
            <SensorCard key={reading.device_id} reading={reading} />
          ))}
        </div>
      )}

      {/* Settings link */}
      {!isLoading && !isError && enabledReadings.length > 0 && (
        <div className="page-footer">
          <Link to="/system/environment" className="settings-link">
            Manage Sensors in Settings
          </Link>
        </div>
      )}
    </div>
  );
}
