/**
 * Modal for starting a new observation (timelapse or recording)
 * Touch-screen friendly - no keyboard required
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { Modal } from "../Modal";
import { Button } from "../Button";
import { TouchNumberInput } from "../TouchNumberInput";
import { TouchSelect } from "../TouchSelect";
import { useToast } from "../../contexts/ToastContext";
import "./StartObservationModal.css";

type ObservationType = "timelapse" | "recording";
type TimeUnit = "seconds" | "minutes" | "hours";
type EndMode = "duration" | "manual";
type OverlayPosition = "tl" | "tr" | "bl" | "br";

interface StartObservationModalProps {
  cameraId: number;
  isOpen: boolean;
  onClose: () => void;
  onStarted: () => void;
}

// Preset options for quick selection
const INTERVAL_PRESETS = [
  { value: 10, unit: "seconds" as TimeUnit, label: "10s" },
  { value: 30, unit: "seconds" as TimeUnit, label: "30s" },
  { value: 1, unit: "minutes" as TimeUnit, label: "1m" },
  { value: 5, unit: "minutes" as TimeUnit, label: "5m" },
  { value: 10, unit: "minutes" as TimeUnit, label: "10m" },
];

const DURATION_PRESETS = [
  { value: 1, unit: "hours" as TimeUnit, label: "1h" },
  { value: 2, unit: "hours" as TimeUnit, label: "2h" },
  { value: 6, unit: "hours" as TimeUnit, label: "6h" },
  { value: 12, unit: "hours" as TimeUnit, label: "12h" },
  { value: 24, unit: "hours" as TimeUnit, label: "24h" },
];

const TIME_UNIT_OPTIONS = [
  { value: "seconds" as TimeUnit, label: "Sec" },
  { value: "minutes" as TimeUnit, label: "Min" },
  { value: "hours" as TimeUnit, label: "Hr" },
];

const OUTPUT_FPS_OPTIONS = [
  { value: 15, label: "15" },
  { value: 24, label: "24" },
  { value: 30, label: "30" },
  { value: 60, label: "60" },
];

const OVERLAY_POSITION_OPTIONS = [
  { value: "tl" as OverlayPosition, label: "Top Left" },
  { value: "tr" as OverlayPosition, label: "Top Right" },
  { value: "bl" as OverlayPosition, label: "Bottom Left" },
  { value: "br" as OverlayPosition, label: "Bottom Right" },
];

interface EnvironmentDevice {
  id: number;
  name: string;
  device_type: string;
  enabled: boolean;
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

  // Environment overlay settings
  const [envOverlayDeviceId, setEnvOverlayDeviceId] = useState<number | null>(null);
  const [envOverlayPosition, setEnvOverlayPosition] = useState<OverlayPosition>("br");
  const [envOverlayShowGraph, setEnvOverlayShowGraph] = useState(false);

  // Fetch environment devices for overlay dropdown
  const { data: envDevicesData } = useQuery({
    queryKey: ["environmentDevices"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/environment/devices");
      if (response.error) throw new Error("Failed to fetch environment devices");
      return response.data as { devices: EnvironmentDevice[] };
    },
    staleTime: 30000,
  });

  const enabledEnvDevices = envDevicesData?.devices?.filter(d => d.enabled) || [];

  // Apply interval preset
  const applyIntervalPreset = (preset: typeof INTERVAL_PRESETS[0]) => {
    setIntervalValue(preset.value);
    setIntervalUnit(preset.unit);
  };

  // Apply duration preset
  const applyDurationPreset = (preset: typeof DURATION_PRESETS[0]) => {
    setTlDurationValue(preset.value);
    setTlDurationUnit(preset.unit);
  };

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
          // Environment overlay settings
          env_overlay_device_id: envOverlayDeviceId,
          env_overlay_position: envOverlayDeviceId ? envOverlayPosition : "br",
          env_overlay_show_graph: envOverlayDeviceId ? envOverlayShowGraph : false,
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
            </button>
          </div>
        </div>

        {/* Timelapse Settings */}
        {observationType === "timelapse" && (
          <div className="observation-modal__settings">
            {/* Interval Presets */}
            <div className="observation-modal__section">
              <label className="observation-modal__section-label">
                Capture Every
              </label>
              <div className="observation-modal__presets">
                {INTERVAL_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    className={`observation-modal__preset ${
                      intervalValue === preset.value &&
                      intervalUnit === preset.unit
                        ? "observation-modal__preset--active"
                        : ""
                    }`}
                    onClick={() => applyIntervalPreset(preset)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <div className="observation-modal__custom-row">
                <TouchNumberInput
                  value={intervalValue}
                  onChange={setIntervalValue}
                  min={1}
                  max={999}
                  className="observation-modal__number-input"
                />
                <TouchSelect
                  value={intervalUnit}
                  onChange={setIntervalUnit}
                  options={TIME_UNIT_OPTIONS}
                  className="observation-modal__unit-select"
                />
              </div>
            </div>

            {/* End Mode */}
            <div className="observation-modal__section">
              <label className="observation-modal__section-label">
                Run Until
              </label>
              <TouchSelect
                value={tlEndMode}
                onChange={setTlEndMode}
                options={[
                  { value: "duration" as EndMode, label: "Set Duration" },
                  { value: "manual" as EndMode, label: "Manual Stop" },
                ]}
              />
            </div>

            {/* Duration (if duration mode) */}
            {tlEndMode === "duration" && (
              <div className="observation-modal__section">
                <label className="observation-modal__section-label">
                  Duration
                </label>
                <div className="observation-modal__presets">
                  {DURATION_PRESETS.map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      className={`observation-modal__preset ${
                        tlDurationValue === preset.value &&
                        tlDurationUnit === preset.unit
                          ? "observation-modal__preset--active"
                          : ""
                      }`}
                      onClick={() => applyDurationPreset(preset)}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <div className="observation-modal__custom-row">
                  <TouchNumberInput
                    value={tlDurationValue}
                    onChange={setTlDurationValue}
                    min={1}
                    max={999}
                    className="observation-modal__number-input"
                  />
                  <TouchSelect
                    value={tlDurationUnit}
                    onChange={setTlDurationUnit}
                    options={TIME_UNIT_OPTIONS}
                    className="observation-modal__unit-select"
                  />
                </div>
              </div>
            )}

            {/* Output FPS */}
            <div className="observation-modal__section">
              <label className="observation-modal__section-label">
                Output Video FPS
              </label>
              <TouchSelect
                value={outputFps}
                onChange={setOutputFps}
                options={OUTPUT_FPS_OPTIONS}
              />
            </div>

            {/* Environment Overlay */}
            {enabledEnvDevices.length > 0 && (
              <>
                <div className="observation-modal__divider" />
                <div className="observation-modal__section">
                  <label className="observation-modal__section-label">
                    Environment Overlay
                  </label>
                  <TouchSelect
                    value={envOverlayDeviceId ?? 0}
                    onChange={(val) => setEnvOverlayDeviceId(val === 0 ? null : val)}
                    options={[
                      { value: 0, label: "None" },
                      ...enabledEnvDevices.map(d => ({
                        value: d.id,
                        label: `${d.name} (${d.device_type})`,
                      })),
                    ]}
                  />
                </div>

                {envOverlayDeviceId && (
                  <>
                    <div className="observation-modal__section">
                      <label className="observation-modal__section-label">
                        Overlay Position
                      </label>
                      <TouchSelect
                        value={envOverlayPosition}
                        onChange={setEnvOverlayPosition}
                        options={OVERLAY_POSITION_OPTIONS}
                      />
                    </div>

                    <div className="observation-modal__section">
                      <label className="observation-modal__section-label">
                        Show Temperature Graph
                      </label>
                      <TouchSelect
                        value={envOverlayShowGraph ? 1 : 0}
                        onChange={(val) => setEnvOverlayShowGraph(val === 1)}
                        options={[
                          { value: 0, label: "No" },
                          { value: 1, label: "Yes" },
                        ]}
                      />
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* Recording Settings */}
        {observationType === "recording" && (
          <div className="observation-modal__settings">
            {/* End Mode */}
            <div className="observation-modal__section">
              <label className="observation-modal__section-label">
                Record Until
              </label>
              <TouchSelect
                value={recEndMode}
                onChange={setRecEndMode}
                options={[
                  { value: "manual" as EndMode, label: "Manual Stop" },
                  { value: "duration" as EndMode, label: "Set Duration" },
                ]}
              />
            </div>

            {/* Duration (if duration mode) */}
            {recEndMode === "duration" && (
              <div className="observation-modal__section">
                <label className="observation-modal__section-label">
                  Duration
                </label>
                <div className="observation-modal__custom-row">
                  <TouchNumberInput
                    value={recDurationValue}
                    onChange={setRecDurationValue}
                    min={1}
                    max={999}
                    className="observation-modal__number-input"
                  />
                  <TouchSelect
                    value={recDurationUnit}
                    onChange={setRecDurationUnit}
                    options={TIME_UNIT_OPTIONS}
                    className="observation-modal__unit-select"
                  />
                </div>
              </div>
            )}

            <p className="observation-modal__note">
              Recording uses H.264 at 4 Mbps. Only one recording active at a
              time due to hardware encoder limits.
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="observation-modal__footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            className="observation-modal__btn"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={startMutation.isPending}
            className="observation-modal__btn observation-modal__btn--primary"
          >
            {startMutation.isPending ? "Starting..." : "Start"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
