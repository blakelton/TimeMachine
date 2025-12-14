/**
 * Camera status card component with real-time job status
 */

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "../api/client";
import "./CameraStatusCard.css";

interface Camera {
  id: number;
  name: string;
  camera_type: string;
  enabled: boolean;
  device_path?: string;
}

interface CameraStatusCardProps {
  camera: Camera;
}

export function CameraStatusCard({ camera }: CameraStatusCardProps) {
  // Check for active jobs on this camera
  const { data: jobsData } = useQuery({
    queryKey: ["cameraJobs", camera.id],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/jobs/running", {
        params: { query: { camera_id: camera.id } },
      });
      if (error) throw error;
      return data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });

  // Determine current activity
  const activeJob = (jobsData?.jobs || []).find(
    (job) => job.status === "running" || job.status === "pending"
  );

  const getStatusInfo = () => {
    if (!camera.enabled) {
      return {
        status: "disabled",
        icon: "⏸️",
        text: "Disabled",
        color: "disabled",
      };
    }

    if (activeJob) {
      if (activeJob.job_type === "recording") {
        return {
          status: "recording",
          icon: "🔴",
          text: "Recording",
          color: "recording",
        };
      }
      if (activeJob.job_type === "timelapse") {
        return {
          status: "timelapse",
          icon: "⏱️",
          text: "Timelapse",
          color: "timelapse",
        };
      }
    }

    // Camera is available (enabled, no active job)
    return {
      status: "available",
      icon: "✅",
      text: "Available",
      color: "available",
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <Link
      to={`/camera/${camera.id}`}
      className={`camera-status-card ${statusInfo.color}`}
    >
      <div className="camera-header">
        <div className="camera-info">
          <h3 className="camera-name">{camera.name}</h3>
          <span className="camera-type">{camera.camera_type.toUpperCase()}</span>
        </div>
        <div className="camera-status">
          <span className="status-icon">{statusInfo.icon}</span>
          <span className="status-text">{statusInfo.text}</span>
        </div>
      </div>

      {activeJob && (
        <div className="camera-activity">
          <span className="activity-indicator" />
          <span className="activity-text">
            {activeJob.job_type === "recording"
              ? "Recording in progress"
              : "Timelapse capturing"}
          </span>
        </div>
      )}
    </Link>
  );
}
