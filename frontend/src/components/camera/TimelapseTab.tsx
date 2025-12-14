/**
 * Timelapse tab - Timelapse controls and management
 */

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { FormField } from "../FormField";
import { ConfirmDialog } from "../ConfirmDialog";
import { DiskSpaceWarning } from "./DiskSpaceWarning";
import { TimelapseResumeBar, type InterruptedTimelapse } from "./TimelapseResumeBar";
import { TimelapseCleanupDialog } from "./TimelapseCleanupDialog";
import { useToast } from "../../contexts/ToastContext";
import { wsClient } from "../../lib/websocket";
import { useWebSocketMessage } from "../../hooks/useWebSocket";
import type { WSStatsUpdate, WSJobUpdate } from "../../types/websocket";
import "./TimelapseTab.css";

export interface TimelapseTabProps {
  cameraId: number;
}

export function TimelapseTab({ cameraId }: TimelapseTabProps) {
  const [interval, setInterval] = useState("60");
  const [duration, setDuration] = useState("3600");
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [framesCaptured, setFramesCaptured] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [diskFreeGB, setDiskFreeGB] = useState<number>(0);
  const [diskTotalGB, setDiskTotalGB] = useState<number>(0);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [interrupted, setInterrupted] = useState<InterruptedTimelapse | null>(null);
  const [showCleanupDialog, setShowCleanupDialog] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const toast = useToast();

  // Subscribe to WebSocket stats updates for disk space
  useWebSocketMessage<WSStatsUpdate>(wsClient, "stats_update", (message) => {
    setDiskFreeGB(message.disk_free_gb);
    if (diskTotalGB === 0) {
      setDiskTotalGB(message.disk_free_gb * 2);
    }
  });

  // Subscribe to job updates to track timelapse status
  useWebSocketMessage<WSJobUpdate>(wsClient, "job_update", (message) => {
    if (message.camera_id === cameraId && message.job_type === "timelapse") {
      if (message.status === "running") {
        setIsRunning(true);
        if (message.progress !== null && message.progress !== undefined) {
          // Progress is 0-100, convert to frames
          const totalFramesEstimate = totalFrames || 100;
          const capturedFrames = Math.floor(
            (message.progress / 100) * totalFramesEstimate
          );
          setFramesCaptured(capturedFrames);
        }
      } else if (message.status === "completed" || message.status === "failed" || message.status === "interrupted") {
        setIsRunning(false);
        setFramesCaptured(0);
        setTotalFrames(0);
        if (message.status === "completed") {
          toast.success("Timelapse completed");
        } else if (message.status === "interrupted") {
          // Refresh to check for interrupted state
          checkInterrupted();
        } else {
          toast.error("Timelapse failed");
        }
      }
    }
  });

  // Calculate estimated frames
  useEffect(() => {
    const intervalNum = parseInt(interval);
    const durationNum = parseInt(duration);
    if (!isNaN(intervalNum) && !isNaN(durationNum) && intervalNum > 0) {
      const estimatedFrames = Math.floor(durationNum / intervalNum);
      setTotalFrames(estimatedFrames);
    }
  }, [interval, duration]);

  // Check for interrupted timelapse on mount
  const checkInterrupted = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/v1/cameras/${cameraId}/timelapse/interrupted`
      );
      if (!response.ok) return;

      const data = await response.json();
      if (data.has_interrupted) {
        setInterrupted({
          job_id: data.job_id,
          frame_count: data.frame_count,
          disk_usage_human: data.disk_usage_human,
          started_at: data.started_at,
          interrupted_at: data.interrupted_at,
          original_config: data.original_config,
        });
      } else {
        setInterrupted(null);
      }
    } catch (error) {
      console.error("Failed to check interrupted timelapse:", error);
    }
  }, [cameraId]);

  useEffect(() => {
    checkInterrupted();
  }, [checkInterrupted]);

  const handleResume = async () => {
    setResumeLoading(true);
    try {
      const response = await fetch(
        `/api/v1/cameras/${cameraId}/timelapse/resume`,
        { method: "POST" }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to resume timelapse");
      }

      toast.success("Timelapse resumed");
      setInterrupted(null);
      setIsRunning(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to resume");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleFinalize = async () => {
    setResumeLoading(true);
    try {
      const response = await fetch(
        `/api/v1/cameras/${cameraId}/timelapse/finalize`,
        { method: "POST" }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to generate video");
      }

      toast.success("Video generation started");
      setInterrupted(null);
      setShowCleanupDialog(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to finalize");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleCleanup = async () => {
    setResumeLoading(true);
    try {
      const response = await fetch(
        `/api/v1/cameras/${cameraId}/timelapse/cleanup`,
        { method: "DELETE" }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to cleanup");
      }

      const data = await response.json();
      toast.success(`Deleted ${data.frames_deleted} frames, freed ${data.space_freed_human}`);
      setInterrupted(null);
      setShowCleanupDialog(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to cleanup");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleStartTimelapse = async () => {
    // Validate inputs
    const intervalNum = parseInt(interval);
    if (isNaN(intervalNum) || intervalNum <= 0) {
      toast.error("Please enter a valid interval");
      return;
    }

    const durationNum = parseInt(duration);
    if (isNaN(durationNum) || durationNum <= 0) {
      toast.error("Please enter a valid duration");
      return;
    }

    if (intervalNum >= durationNum) {
      toast.error("Interval must be less than duration");
      return;
    }

    // Check disk space
    const freePercent = diskTotalGB > 0 ? (diskFreeGB / diskTotalGB) * 100 : 100;
    if (freePercent < 5) {
      toast.error("Insufficient disk space to start timelapse");
      return;
    }

    setIsLoading(true);

    try {
      // Calculate total_frames from duration and interval
      const totalFramesCalc = Math.floor(durationNum / intervalNum);

      const { error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/timelapse/start" as any,
        {
          params: { path: { camera_id: cameraId } },
          body: {
            config: {
              interval_seconds: intervalNum,
              total_frames: totalFramesCalc,
            },
          },
        }
      );

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to start timelapse";
        throw new Error(errorMessage);
      }

      setIsRunning(true);
      setFramesCaptured(0);
      toast.success("Timelapse started");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start timelapse";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopTimelapse = async () => {
    setShowStopConfirm(false);
    setIsLoading(true);

    try {
      const { error } = await apiClient.POST(
        "/api/v1/cameras/{camera_id}/timelapse/stop" as any,
        {
          params: { path: { camera_id: cameraId } },
        }
      );

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to stop timelapse";
        throw new Error(errorMessage);
      }

      setIsRunning(false);
      setFramesCaptured(0);
      toast.success("Timelapse stopped");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to stop timelapse";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const progressPercent =
    totalFrames > 0 ? (framesCaptured / totalFrames) * 100 : 0;
  const criticalThreshold = diskTotalGB > 0 ? (diskFreeGB / diskTotalGB) * 100 : 100;

  return (
    <div className="timelapse-tab">
      <DiskSpaceWarning
        diskFreeGB={diskFreeGB}
        diskTotalGB={diskTotalGB}
        warningThresholdPercent={10}
        criticalThresholdPercent={5}
      />

      {interrupted && (
        <TimelapseResumeBar
          interrupted={interrupted}
          onResume={handleResume}
          onFinalize={handleFinalize}
          onCleanup={() => setShowCleanupDialog(true)}
          loading={resumeLoading}
        />
      )}

      <div className="timelapse-tab__controls">
        <FormField
          label="Interval (seconds)"
          id="interval-input"
          helperText="Time between captures"
          type="number"
          value={interval}
          onChange={(e) => setInterval(e.target.value)}
          disabled={isRunning || isLoading}
          min={1}
          max={3600}
        />

        <FormField
          label="Duration (seconds)"
          id="duration-input"
          helperText="Total timelapse duration"
          type="number"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          disabled={isRunning || isLoading}
          min={1}
        />

        <div className="timelapse-tab__info">
          <span className="timelapse-tab__info-label">Estimated frames:</span>
          <span className="timelapse-tab__info-value">{totalFrames}</span>
        </div>

        <div className="timelapse-tab__actions">
          {!isRunning ? (
            <Button
              variant="primary"
              onClick={handleStartTimelapse}
              disabled={isLoading || criticalThreshold < 5}
            >
              {isLoading ? "Starting..." : "Start Timelapse"}
            </Button>
          ) : (
            <Button
              variant="danger"
              onClick={() => setShowStopConfirm(true)}
              disabled={isLoading}
            >
              {isLoading ? "Stopping..." : "Stop Timelapse"}
            </Button>
          )}
        </div>
      </div>

      {isRunning && (
        <div className="timelapse-tab__status">
          <div className="timelapse-tab__status-header">
            <div className="timelapse-tab__status-indicator">
              <span className="timelapse-tab__recording-dot"></span>
              <span className="timelapse-tab__recording-text">
                Timelapse Running
              </span>
            </div>
            <div className="timelapse-tab__frames">
              {framesCaptured} / {totalFrames} frames
            </div>
          </div>
          <div className="timelapse-tab__progress">
            <div
              className="timelapse-tab__progress-bar"
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            ></div>
          </div>
          <div className="timelapse-tab__progress-text">
            {progressPercent.toFixed(1)}% complete
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={showStopConfirm}
        title="Stop Timelapse"
        message="Are you sure you want to stop the timelapse? Captured frames will be saved."
        confirmText="Stop Timelapse"
        cancelText="Continue"
        variant="danger"
        onConfirm={handleStopTimelapse}
        onClose={() => setShowStopConfirm(false)}
      />

      <TimelapseCleanupDialog
        isOpen={showCleanupDialog}
        frameCount={interrupted?.frame_count || 0}
        diskUsage={interrupted?.disk_usage_human || "0 B"}
        onFinalize={handleFinalize}
        onDelete={handleCleanup}
        onCancel={() => setShowCleanupDialog(false)}
        loading={resumeLoading}
      />
    </div>
  );
}
