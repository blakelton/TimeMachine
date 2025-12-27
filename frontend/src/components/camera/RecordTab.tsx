/**
 * Record tab - Video recording controls
 */

import { useState, useEffect } from "react";
import { startRecording, stopRecording } from "../../api";
import { Button } from "../Button";
import { FormField } from "../FormField";
import { ConfirmDialog } from "../ConfirmDialog";
import { DiskSpaceWarning } from "./DiskSpaceWarning";
import { useToast } from "../../contexts/ToastContext";
import { wsClient } from "../../lib/websocket";
import { useWebSocketMessage } from "../../hooks/useWebSocket";
import type { WSStatsUpdate, WSJobUpdate } from "../../types/websocket";
import "./RecordTab.css";

export interface RecordTabProps {
  cameraId: number;
}

export function RecordTab({ cameraId }: RecordTabProps) {
  const [bitrate, setBitrate] = useState("2000000");
  const [duration, setDuration] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [recordingStartTime, setRecordingStartTime] = useState<Date | null>(
    null
  );
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [diskFreeGB, setDiskFreeGB] = useState<number>(0);
  const [diskTotalGB, setDiskTotalGB] = useState<number>(0);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const toast = useToast();

  // Subscribe to WebSocket stats updates for disk space
  useWebSocketMessage<WSStatsUpdate>(wsClient, "stats_update", (message) => {
    setDiskFreeGB(message.disk_free_gb);
    // Estimate total disk based on free space (this is approximate)
    // In a real scenario, the backend should provide total disk size
    if (diskTotalGB === 0) {
      setDiskTotalGB(message.disk_free_gb * 2); // Rough estimate
    }
  });

  // Subscribe to job updates to track recording status
  useWebSocketMessage<WSJobUpdate>(wsClient, "job_update", (message) => {
    if (message.camera_id === cameraId && message.job_type === "recording") {
      if (message.status === "running") {
        setIsRecording(true);
      } else if (message.status === "completed" || message.status === "failed" || message.status === "interrupted") {
        setIsRecording(false);
        setRecordingStartTime(null);
        setElapsedSeconds(0);
        if (message.status === "completed") {
          toast.success("Recording completed");
        } else {
          toast.error("Recording failed");
        }
      }
    }
  });

  // Timer for elapsed time
  useEffect(() => {
    let interval: number | undefined;
    if (isRecording && recordingStartTime) {
      interval = window.setInterval(() => {
        const elapsed = Math.floor(
          (Date.now() - recordingStartTime.getTime()) / 1000
        );
        setElapsedSeconds(elapsed);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording, recordingStartTime]);

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleStartRecording = async () => {
    // Validate inputs
    const bitrateNum = parseInt(bitrate);
    if (isNaN(bitrateNum) || bitrateNum <= 0) {
      toast.error("Please enter a valid bitrate");
      return;
    }

    const durationNum = duration ? parseInt(duration) : undefined;
    if (duration && (isNaN(durationNum!) || durationNum! <= 0)) {
      toast.error("Please enter a valid duration");
      return;
    }

    // Check disk space
    const freePercent = diskTotalGB > 0 ? (diskFreeGB / diskTotalGB) * 100 : 100;
    if (freePercent < 5) {
      toast.error("Insufficient disk space to start recording");
      return;
    }

    setIsLoading(true);

    try {
      const { error } = await startRecording(cameraId, durationNum);

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to start recording";
        throw new Error(errorMessage);
      }

      setIsRecording(true);
      setRecordingStartTime(new Date());
      setElapsedSeconds(0);
      toast.success("Recording started");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start recording";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopRecording = async () => {
    setShowStopConfirm(false);
    setIsLoading(true);

    try {
      const { error } = await stopRecording(cameraId);

      if (error) {
        const errorMessage = typeof error.detail === 'string' ? error.detail : "Failed to stop recording";
        throw new Error(errorMessage);
      }

      setIsRecording(false);
      setRecordingStartTime(null);
      setElapsedSeconds(0);
      toast.success("Recording stopped");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to stop recording";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const criticalThreshold = diskTotalGB > 0 ? (diskFreeGB / diskTotalGB) * 100 : 100;

  return (
    <div className="record-tab">
      <DiskSpaceWarning
        diskFreeGB={diskFreeGB}
        diskTotalGB={diskTotalGB}
        warningThresholdPercent={10}
        criticalThresholdPercent={5}
      />

      <div className="record-tab__controls">
        <FormField
          label="Bitrate (bps)"
          id="bitrate-input"
          helperText="Higher bitrate = better quality, larger files"
          type="number"
          value={bitrate}
          onChange={(e) => setBitrate(e.target.value)}
          disabled={isRecording || isLoading}
          min={500000}
          max={10000000}
          step={100000}
        />

        <FormField
          label="Duration (seconds)"
          id="duration-input"
          helperText="Leave empty for manual stop"
          type="number"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          disabled={isRecording || isLoading}
          min={1}
          placeholder="Optional"
        />

        <div className="record-tab__actions">
          {!isRecording ? (
            <Button
              variant="primary"
              onClick={handleStartRecording}
              disabled={isLoading || criticalThreshold < 5}
            >
              {isLoading ? "Starting..." : "Start Recording"}
            </Button>
          ) : (
            <Button
              variant="danger"
              onClick={() => setShowStopConfirm(true)}
              disabled={isLoading}
            >
              {isLoading ? "Stopping..." : "Stop Recording"}
            </Button>
          )}
        </div>
      </div>

      {isRecording && (
        <div className="record-tab__status">
          <div className="record-tab__status-indicator">
            <span className="record-tab__recording-dot"></span>
            <span className="record-tab__recording-text">Recording</span>
          </div>
          <div className="record-tab__timer">{formatTime(elapsedSeconds)}</div>
          {duration && (
            <div className="record-tab__progress">
              <div
                className="record-tab__progress-bar"
                style={{
                  width: `${Math.min(
                    (elapsedSeconds / parseInt(duration)) * 100,
                    100
                  )}%`,
                }}
              ></div>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={showStopConfirm}
        title="Stop Recording"
        message="Are you sure you want to stop the recording?"
        confirmText="Stop Recording"
        cancelText="Continue Recording"
        variant="danger"
        onConfirm={handleStopRecording}
        onClose={() => setShowStopConfirm(false)}
      />
    </div>
  );
}
