/**
 * Modal for starting a new observation (timelapse or recording)
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { Modal } from "../Modal";
import { Button } from "../Button";
import { FormField } from "../FormField";
import { useToast } from "../../contexts/ToastContext";
import "./StartObservationModal.css";

type ObservationType = "timelapse" | "recording";
type TimeUnit = "seconds" | "minutes" | "hours";
type EndMode = "duration" | "datetime" | "manual";

interface StartObservationModalProps {
  cameraId: number;
  isOpen: boolean;
  onClose: () => void;
  onStarted: () => void;
}

export function StartObservationModal({
  cameraId,
  isOpen,
  onClose,
  onStarted,
}: StartObservationModalProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Observation type selection
  const [observationType, setObservationType] =
    useState<ObservationType>("timelapse");

  // Timelapse settings
  const [intervalValue, setIntervalValue] = useState(1);
  const [intervalUnit, setIntervalUnit] = useState<TimeUnit>("minutes");
  const [tlEndMode, setTlEndMode] = useState<EndMode>("duration");
  const [tlDurationValue, setTlDurationValue] = useState(1);
  const [tlDurationUnit, setTlDurationUnit] = useState<TimeUnit>("hours");
  const [outputFps, setOutputFps] = useState(30);

  // Recording settings
  const [recEndMode, setRecEndMode] = useState<EndMode>("manual");
  const [recDurationValue, setRecDurationValue] = useState(30);
  const [recDurationUnit, setRecDurationUnit] = useState<TimeUnit>("minutes");

  // Mutation for starting observation
  const startMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        camera_id: cameraId,
        observation_type: observationType,
      };

      if (observationType === "timelapse") {
        body.timelapse_config = {
          interval_value: intervalValue,
          interval_unit: intervalUnit,
          end_mode: tlEndMode,
          duration_value: tlEndMode === "duration" ? tlDurationValue : null,
          duration_unit: tlEndMode === "duration" ? tlDurationUnit : null,
          output_fps: outputFps,
          resolution_width: 1920,
          resolution_height: 1080,
          quality: 95,
        };
      } else {
        body.recording_config = {
          end_mode: recEndMode,
          duration_value: recEndMode === "duration" ? recDurationValue : null,
          duration_unit: recEndMode === "duration" ? recDurationUnit : null,
          bitrate_kbps: 4000,
          resolution_width: 1920,
          resolution_height: 1080,
        };
      }

      const { data, error } = await apiClient.POST(
        "/api/v1/observations/start" as any,
        { body }
      );

      if (error) {
        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : "Failed to start observation"
        );
      }

      return data;
    },
    onSuccess: (data: any) => {
      if (data?.success) {
        toast.success(data.message || "Observation started");
        queryClient.invalidateQueries({ queryKey: ["activeJobs", cameraId] });
        queryClient.invalidateQueries({
          queryKey: ["activeObservation", cameraId],
        });
        onStarted();
        onClose();
      } else {
        toast.error(data?.message || "Failed to start observation");
      }
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    startMutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Start Observation"
      width="lg"
    >
      <form onSubmit={handleSubmit} className="observation-modal">
        {/* Observation Type Selector */}
        <div className="observation-modal__type-selector">
          <label className="observation-modal__type-label">
            Observation Type
          </label>
          <div className="observation-modal__type-options">
            <button
              type="button"
              className={`observation-modal__type-option ${
                observationType === "timelapse"
                  ? "observation-modal__type-option--active"
                  : ""
              }`}
              onClick={() => setObservationType("timelapse")}
            >
              <span className="observation-modal__type-icon">⏱️</span>
              <span className="observation-modal__type-name">Time-Lapse</span>
              <span className="observation-modal__type-desc">
                Capture frames at intervals
              </span>
            </button>
            <button
              type="button"
              className={`observation-modal__type-option ${
                observationType === "recording"
                  ? "observation-modal__type-option--active"
                  : ""
              }`}
              onClick={() => setObservationType("recording")}
            >
              <span className="observation-modal__type-icon">🎬</span>
              <span className="observation-modal__type-name">Recording</span>
              <span className="observation-modal__type-desc">
                Continuous video recording
              </span>
            </button>
          </div>
        </div>

        <div className="observation-modal__divider" />

        {/* Timelapse Settings */}
        {observationType === "timelapse" && (
          <div className="observation-modal__settings">
            <h3 className="observation-modal__settings-title">
              Timelapse Settings
            </h3>

            {/* Interval */}
            <div className="observation-modal__row">
              <FormField
                label="Capture Interval"
                type="number"
                value={intervalValue}
                onChange={(e) => setIntervalValue(Number(e.target.value))}
                min={1}
                max={999}
                className="observation-modal__field--narrow"
              />
              <FormField
                label="Unit"
                element="select"
                value={intervalUnit}
                onChange={(e) => setIntervalUnit(e.target.value as TimeUnit)}
                className="observation-modal__field--narrow"
              >
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
              </FormField>
            </div>

            {/* End Mode */}
            <FormField
              label="Run Until"
              element="select"
              value={tlEndMode}
              onChange={(e) => setTlEndMode(e.target.value as EndMode)}
            >
              <option value="duration">For a Duration</option>
              <option value="manual">Until Manually Stopped</option>
            </FormField>

            {/* Duration (if duration mode) */}
            {tlEndMode === "duration" && (
              <div className="observation-modal__row">
                <FormField
                  label="Duration"
                  type="number"
                  value={tlDurationValue}
                  onChange={(e) => setTlDurationValue(Number(e.target.value))}
                  min={1}
                  max={999}
                  className="observation-modal__field--narrow"
                />
                <FormField
                  label="Unit"
                  element="select"
                  value={tlDurationUnit}
                  onChange={(e) =>
                    setTlDurationUnit(e.target.value as TimeUnit)
                  }
                  className="observation-modal__field--narrow"
                >
                  <option value="seconds">Seconds</option>
                  <option value="minutes">Minutes</option>
                  <option value="hours">Hours</option>
                </FormField>
              </div>
            )}

            {/* Output FPS */}
            <FormField
              label="Output Video FPS"
              element="select"
              value={outputFps}
              onChange={(e) => setOutputFps(Number(e.target.value))}
            >
              <option value={15}>15 fps</option>
              <option value={24}>24 fps</option>
              <option value={30}>30 fps (recommended)</option>
              <option value={60}>60 fps</option>
            </FormField>
          </div>
        )}

        {/* Recording Settings */}
        {observationType === "recording" && (
          <div className="observation-modal__settings">
            <h3 className="observation-modal__settings-title">
              Recording Settings
            </h3>

            {/* End Mode */}
            <FormField
              label="Record Until"
              element="select"
              value={recEndMode}
              onChange={(e) => setRecEndMode(e.target.value as EndMode)}
            >
              <option value="manual">Until Manually Stopped</option>
              <option value="duration">For a Duration</option>
            </FormField>

            {/* Duration (if duration mode) */}
            {recEndMode === "duration" && (
              <div className="observation-modal__row">
                <FormField
                  label="Duration"
                  type="number"
                  value={recDurationValue}
                  onChange={(e) => setRecDurationValue(Number(e.target.value))}
                  min={1}
                  max={999}
                  className="observation-modal__field--narrow"
                />
                <FormField
                  label="Unit"
                  element="select"
                  value={recDurationUnit}
                  onChange={(e) =>
                    setRecDurationUnit(e.target.value as TimeUnit)
                  }
                  className="observation-modal__field--narrow"
                >
                  <option value="seconds">Seconds</option>
                  <option value="minutes">Minutes</option>
                  <option value="hours">Hours</option>
                </FormField>
              </div>
            )}

            <p className="observation-modal__note">
              Recording uses H.264 encoding at 4 Mbps. Only one recording can be
              active at a time due to hardware encoder limitations.
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="observation-modal__footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={startMutation.isPending}
          >
            {startMutation.isPending ? "Starting..." : "Start Observation"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
