/**
 * Form for adding/editing environment devices
 */

import { Button } from "../Button";
import { FormField } from "../FormField";
import type { components } from "../../types/api";

type DeviceTypeInfo = components["schemas"]["DeviceTypeInfo"];

export interface DeviceFormData {
  name: string;
  device_type: string;
  pin_or_address: string;
  enabled: boolean;
  poll_interval_seconds: number;
  temperature_unit: "C" | "F";
  notes: string;
  // Target values
  target_temperature: string;
  target_humidity: string;
  temperature_tolerance: string;
  humidity_tolerance: string;
}

interface EnvironmentDeviceFormProps {
  formData: DeviceFormData;
  formErrors: Partial<Record<keyof DeviceFormData, string>>;
  deviceTypes: DeviceTypeInfo[];
  isEdit: boolean;
  isPending: boolean;
  onChange: (field: keyof DeviceFormData, value: string | boolean | number) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

export function EnvironmentDeviceForm({
  formData,
  formErrors,
  deviceTypes,
  isEdit,
  isPending,
  onChange,
  onSubmit,
  onCancel,
}: EnvironmentDeviceFormProps) {
  const selectedDeviceType = deviceTypes.find((dt) => dt.type === formData.device_type);

  return (
    <div className="device-form">
      <FormField
        label="Device Name"
        type="text"
        value={formData.name}
        onChange={(e) => onChange("name", e.target.value)}
        error={formErrors.name}
        placeholder="e.g., Chamber Sensor 1"
        required
        disabled={isPending}
      />

      <FormField
        element="select"
        label="Device Type"
        value={formData.device_type}
        onChange={(e) => onChange("device_type", e.target.value)}
        required
        disabled={isPending}
      >
        {deviceTypes.map((dt) => (
          <option key={dt.type} value={dt.type}>
            {dt.name}
          </option>
        ))}
      </FormField>

      {selectedDeviceType && (
        <div className="device-type-info">
          <p>{selectedDeviceType.description}</p>
          <p className="measures">
            <strong>Measures:</strong> {selectedDeviceType.measures.join(", ")}
          </p>
        </div>
      )}

      <FormField
        label={selectedDeviceType?.pin_label || "Pin/Address"}
        type="text"
        value={formData.pin_or_address}
        onChange={(e) => onChange("pin_or_address", e.target.value)}
        error={formErrors.pin_or_address}
        placeholder={selectedDeviceType?.pin_placeholder || ""}
        helperText={`Interface: ${selectedDeviceType?.interface || "GPIO"}`}
        required
        disabled={isPending}
      />

      <FormField
        label="Poll Interval (seconds)"
        type="number"
        value={formData.poll_interval_seconds.toString()}
        onChange={(e) => onChange("poll_interval_seconds", parseInt(e.target.value) || 30)}
        helperText="How often to read from this sensor (5-3600 seconds)"
        disabled={isPending}
      />

      <FormField
        element="select"
        label="Temperature Unit"
        value={formData.temperature_unit}
        onChange={(e) => onChange("temperature_unit", e.target.value)}
        helperText="Display temperature in Celsius or Fahrenheit"
        disabled={isPending}
      >
        <option value="C">Celsius (°C)</option>
        <option value="F">Fahrenheit (°F)</option>
      </FormField>

      {/* Target Values Section */}
      <div className="form-section-header">
        <span>Target Values</span>
        <span className="form-section-hint">Set target values to see how readings compare to normal</span>
      </div>

      <div className="form-row">
        <FormField
          label={`Target Temperature (${formData.temperature_unit === "F" ? "°F" : "°C"})`}
          type="number"
          value={formData.target_temperature}
          onChange={(e) => onChange("target_temperature", e.target.value)}
          placeholder="e.g., 22"
          helperText="Leave empty to disable comparison"
          disabled={isPending}
        />
        <FormField
          label="± Tolerance"
          type="number"
          value={formData.temperature_tolerance}
          onChange={(e) => onChange("temperature_tolerance", e.target.value)}
          placeholder="5"
          helperText="Acceptable range"
          disabled={isPending}
        />
      </div>

      <div className="form-row">
        <FormField
          label="Target Humidity (%)"
          type="number"
          value={formData.target_humidity}
          onChange={(e) => onChange("target_humidity", e.target.value)}
          placeholder="e.g., 50"
          helperText="Leave empty to disable comparison"
          disabled={isPending}
        />
        <FormField
          label="± Tolerance"
          type="number"
          value={formData.humidity_tolerance}
          onChange={(e) => onChange("humidity_tolerance", e.target.value)}
          placeholder="10"
          helperText="Acceptable range"
          disabled={isPending}
        />
      </div>

      <FormField
        label="Notes (optional)"
        type="text"
        value={formData.notes}
        onChange={(e) => onChange("notes", e.target.value)}
        placeholder="e.g., Located in upper left corner"
        disabled={isPending}
      />

      <div className="form-field">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.enabled}
            onChange={(e) => onChange("enabled", e.target.checked)}
            disabled={isPending}
          />
          <span>Enable device</span>
        </label>
        <div className="form-helper">
          Device will be polled for readings when enabled
        </div>
      </div>

      <div className="form-actions">
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={isPending}
        >
          Cancel
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={onSubmit}
          loading={isPending}
        >
          {isEdit ? "Update Device" : "Add Device"}
        </Button>
      </div>
    </div>
  );
}
