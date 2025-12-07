/**
 * Camera status card component with real-time updates
 */

import { useState, useCallback, useEffect } from "react";
import { wsClient } from "../lib/websocket";
import { useWebSocketMessage } from "../hooks/useWebSocket";
import type { WSCameraEvent } from "../types/websocket";
import "./CameraStatusCard.css";

interface Camera {
  id: number;
  name: string;
  type: string;
  enabled: boolean;
  status?: "online" | "offline" | "error";
  currentOperation?: string;
}

interface CameraStatusCardProps {
  camera: Camera;
}

export function CameraStatusCard({ camera }: CameraStatusCardProps) {
  const [status, setStatus] = useState<"online" | "offline" | "error">(
    camera.status || "offline"
  );
  const [lastEvent, setLastEvent] = useState<string | null>(null);

  // Subscribe to camera events from WebSocket
  const handleCameraEvent = useCallback(
    (message: WSCameraEvent) => {
      if (message.camera_id === camera.id) {
        // Update status based on event
        if (message.event === "online") {
          setStatus("online");
          setLastEvent("Camera online");
        } else if (message.event === "offline") {
          setStatus("offline");
          setLastEvent("Camera offline");
        } else if (message.event === "error") {
          setStatus("error");
          setLastEvent(message.message || "Camera error");
        } else if (message.event === "recording_started") {
          setLastEvent("Recording started");
        } else if (message.event === "recording_stopped") {
          setLastEvent("Recording stopped");
        }
      }
    },
    [camera.id]
  );

  useWebSocketMessage(wsClient, "camera_event", handleCameraEvent);

  // Clear last event after 5 seconds
  useEffect(() => {
    if (lastEvent) {
      const timer = setTimeout(() => setLastEvent(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [lastEvent]);

  const getStatusColor = () => {
    if (!camera.enabled) return "disabled";
    switch (status) {
      case "online":
        return "online";
      case "offline":
        return "offline";
      case "error":
        return "error";
      default:
        return "unknown";
    }
  };

  const getStatusIcon = () => {
    if (!camera.enabled) return "⏸️";
    switch (status) {
      case "online":
        return "✅";
      case "offline":
        return "⭕";
      case "error":
        return "❌";
      default:
        return "❓";
    }
  };

  const getStatusText = () => {
    if (!camera.enabled) return "Disabled";
    switch (status) {
      case "online":
        return "Online";
      case "offline":
        return "Offline";
      case "error":
        return "Error";
      default:
        return "Unknown";
    }
  };

  return (
    <div className={`camera-status-card ${getStatusColor()}`}>
      <div className="camera-header">
        <div className="camera-info">
          <h3 className="camera-name">{camera.name}</h3>
          <span className="camera-type">{camera.type}</span>
        </div>
        <div className="camera-status">
          <span className="status-icon">{getStatusIcon()}</span>
          <span className="status-text">{getStatusText()}</span>
        </div>
      </div>

      {lastEvent && (
        <div className="camera-event">
          <span className="event-icon">📢</span>
          <span className="event-text">{lastEvent}</span>
        </div>
      )}

      {camera.currentOperation && (
        <div className="camera-operation">
          <span className="operation-label">Current:</span>
          <span className="operation-text">{camera.currentOperation}</span>
        </div>
      )}
    </div>
  );
}
