/**
 * Sensor card component displaying current readings and history graph
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { SensorGraph } from "./SensorGraph";
import type { components } from "../../types/api";
import "./SensorCard.css";

type DeviceCurrentReading = components["schemas"]["DeviceCurrentReading"];
type EnvironmentReadingResponse = components["schemas"]["EnvironmentReadingResponse"];

interface SensorCardProps {
  reading: DeviceCurrentReading;
}

// Device type display info
const DEVICE_INFO: Record<string, { name: string; icon: string }> = {
  dht22: { name: "DHT22", icon: "🌡️" },
  dht11: { name: "DHT11", icon: "🌡️" },
  am2303: { name: "AM2303", icon: "🌡️" },
  bme280: { name: "BME280", icon: "🌡️" },
  ds18b20: { name: "DS18B20", icon: "🌡️" },
};

// Format temperature with appropriate precision and unit
function formatTemperature(value: number | null | undefined, unit: string = "C"): string {
  if (value === null || value === undefined) return "--";
  const symbol = unit === "F" ? "°F" : "°C";
  return `${value.toFixed(1)}${symbol}`;
}

// Format humidity with appropriate precision
function formatHumidity(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return `${value.toFixed(1)}%`;
}

// Format pressure with appropriate precision
function formatPressure(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return `${value.toFixed(0)} hPa`;
}

// Format timestamp for display
function formatTime(timestamp: string | null | undefined): string {
  if (!timestamp) return "No data";
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// Format deviation with sign
function formatDeviation(value: number | null | undefined, unit: string = ""): string {
  if (value === null || value === undefined) return "";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}${unit}`;
}

// Get status class for styling
function getStatusClass(status: string | undefined): string {
  switch (status) {
    case "high":
      return "status-high";
    case "low":
      return "status-low";
    case "normal":
      return "status-normal";
    default:
      return "";
  }
}

export function SensorCard({ reading }: SensorCardProps) {
  const [hoursRange, setHoursRange] = useState(6);

  const deviceInfo = DEVICE_INFO[reading.device_type] || { name: reading.device_type, icon: "📊" };

  // Determine which measurements this device provides
  const hasTemperature = ["dht22", "dht11", "am2303", "bme280", "ds18b20"].includes(reading.device_type);
  const hasHumidity = ["dht22", "dht11", "am2303", "bme280"].includes(reading.device_type);
  const hasPressure = reading.device_type === "bme280";

  // Fetch historical data for graphs
  const { data: historyData } = useQuery({
    queryKey: ["environment-history", reading.device_id, hoursRange],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/environment/readings/{device_id}/history", {
        params: {
          path: { device_id: reading.device_id },
          query: { hours: hoursRange, limit: 500 },
        },
      });
      if (response.error) {
        throw new Error("Failed to fetch history");
      }
      return response.data;
    },
    refetchInterval: 30000, // Refresh history every 30 seconds
    staleTime: 10000,
  });

  const historyReadings = historyData?.readings || [];

  // Prepare graph data
  const temperatureData = historyReadings
    .filter((r: EnvironmentReadingResponse) => r.temperature !== null)
    .map((r: EnvironmentReadingResponse) => ({
      timestamp: new Date(r.timestamp).getTime(),
      value: r.temperature as number,
    }));

  const humidityData = historyReadings
    .filter((r: EnvironmentReadingResponse) => r.humidity !== null)
    .map((r: EnvironmentReadingResponse) => ({
      timestamp: new Date(r.timestamp).getTime(),
      value: r.humidity as number,
    }));

  const pressureData = historyReadings
    .filter((r: EnvironmentReadingResponse) => r.pressure !== null)
    .map((r: EnvironmentReadingResponse) => ({
      timestamp: new Date(r.timestamp).getTime(),
      value: r.pressure as number,
    }));

  return (
    <div className="sensor-card">
      {/* Header */}
      <div className="sensor-header">
        <div className="sensor-title">
          <span className="sensor-icon">{deviceInfo.icon}</span>
          <h3>{reading.device_name}</h3>
        </div>
        <div className="sensor-type">{deviceInfo.name}</div>
      </div>

      {/* Error state */}
      {reading.error && (
        <div className="sensor-error">
          <span className="error-icon">⚠️</span>
          {reading.error}
        </div>
      )}

      {/* Current readings */}
      <div className="sensor-readings">
        {hasTemperature && (
          <div className={`reading-item temperature ${getStatusClass(reading.temperature_status)}`}>
            <div className="reading-label">Temperature</div>
            <div className="reading-value">{formatTemperature(reading.temperature, reading.temperature_unit)}</div>
            {reading.target_temperature !== null && reading.target_temperature !== undefined && (
              <div className="reading-target">
                <span className="target-label">Target:</span>
                <span className="target-value">
                  {formatTemperature(reading.target_temperature, reading.temperature_unit)}
                </span>
                {reading.temperature_deviation !== null && reading.temperature_deviation !== undefined && (
                  <span className={`deviation ${reading.temperature_status}`}>
                    {formatDeviation(reading.temperature_deviation, reading.temperature_unit === "F" ? "°F" : "°C")}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
        {hasHumidity && (
          <div className={`reading-item humidity ${getStatusClass(reading.humidity_status)}`}>
            <div className="reading-label">Humidity</div>
            <div className="reading-value">{formatHumidity(reading.humidity)}</div>
            {reading.target_humidity !== null && reading.target_humidity !== undefined && (
              <div className="reading-target">
                <span className="target-label">Target:</span>
                <span className="target-value">{formatHumidity(reading.target_humidity)}</span>
                {reading.humidity_deviation !== null && reading.humidity_deviation !== undefined && (
                  <span className={`deviation ${reading.humidity_status}`}>
                    {formatDeviation(reading.humidity_deviation, "%")}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
        {hasPressure && (
          <div className={`reading-item pressure ${getStatusClass(reading.pressure_status)}`}>
            <div className="reading-label">Pressure</div>
            <div className="reading-value">{formatPressure(reading.pressure)}</div>
            {reading.target_pressure !== null && reading.target_pressure !== undefined && (
              <div className="reading-target">
                <span className="target-label">Target:</span>
                <span className="target-value">{formatPressure(reading.target_pressure)}</span>
                {reading.pressure_deviation !== null && reading.pressure_deviation !== undefined && (
                  <span className={`deviation ${reading.pressure_status}`}>
                    {formatDeviation(reading.pressure_deviation, " hPa")}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Time range selector */}
      <div className="graph-controls">
        <span className="controls-label">History:</span>
        <div className="range-buttons">
          {[1, 6, 12, 24].map((hours) => (
            <button
              key={hours}
              className={`range-btn ${hoursRange === hours ? "active" : ""}`}
              onClick={() => setHoursRange(hours)}
            >
              {hours}h
            </button>
          ))}
        </div>
      </div>

      {/* Graphs */}
      <div className="sensor-graphs">
        {hasTemperature && temperatureData.length > 1 && (
          <SensorGraph
            data={temperatureData}
            color="#ef4444"
            label="Temperature"
            unit={reading.temperature_unit === "F" ? "°F" : "°C"}
            height={80}
          />
        )}
        {hasHumidity && humidityData.length > 1 && (
          <SensorGraph
            data={humidityData}
            color="#3b82f6"
            label="Humidity"
            unit="%"
            height={80}
          />
        )}
        {hasPressure && pressureData.length > 1 && (
          <SensorGraph
            data={pressureData}
            color="#8b5cf6"
            label="Pressure"
            unit="hPa"
            height={80}
          />
        )}
        {temperatureData.length <= 1 && humidityData.length <= 1 && (
          <div className="no-graph-data">
            <p>Collecting data...</p>
          </div>
        )}
      </div>

      {/* Last updated */}
      <div className="sensor-footer">
        <span className="last-updated">
          Last reading: {formatTime(reading.timestamp)}
        </span>
      </div>
    </div>
  );
}
