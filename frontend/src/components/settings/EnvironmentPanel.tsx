/**
 * Environment settings panel with Feedback devices section
 */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useApiMutation } from "../../hooks/useApiMutation";
import { Button } from "../Button";
import { Modal } from "../Modal";
import { ConfirmDialog } from "../ConfirmDialog";
import { FormField } from "../FormField";
import type { components } from "../../types/api";
import "./EnvironmentPanel.css";

type EnvironmentDeviceResponse = components["schemas"]["EnvironmentDeviceResponse"];
type EnvironmentDeviceCreate = components["schemas"]["EnvironmentDeviceCreate"];
type EnvironmentDeviceUpdate = components["schemas"]["EnvironmentDeviceUpdate"];
type DeviceTypeInfo = components["schemas"]["DeviceTypeInfo"];

interface DeviceFormData {
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

export function EnvironmentPanel() {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editDevice, setEditDevice] = useState<EnvironmentDeviceResponse | null>(null);
  const [deleteDevice, setDeleteDevice] = useState<EnvironmentDeviceResponse | null>(null);
  const [formData, setFormData] = useState<DeviceFormData>({
    name: "",
    device_type: "dht22",
    pin_or_address: "",
    enabled: true,
    poll_interval_seconds: 10,
    temperature_unit: "C",
    notes: "",
    target_temperature: "",
    target_humidity: "",
    temperature_tolerance: "5",
    humidity_tolerance: "10",
  });
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof DeviceFormData, string>>>({});

  const queryClient = useQueryClient();

  // Fetch device types
  const { data: deviceTypesData } = useQuery({
    queryKey: ["environment-device-types"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/environment/device-types");
      if (response.error) {
        throw new Error("Failed to fetch device types");
      }
      return response.data;
    },
  });

  // Fetch devices
  const { data: devicesData, isLoading, error } = useQuery({
    queryKey: ["environment-devices"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/environment/devices");
      if (response.error) {
        throw new Error("Failed to fetch devices");
      }
      return response.data;
    },
  });

  const deviceTypes = deviceTypesData?.device_types || [];
  const devices = devicesData?.devices || [];

  // Get device type info by type
  const getDeviceTypeInfo = (type: string): DeviceTypeInfo | undefined => {
    return deviceTypes.find((dt) => dt.type === type);
  };

  // Create device mutation
  const createMutation = useApiMutation(
    async (data: DeviceFormData) => {
      const deviceData: EnvironmentDeviceCreate = {
        name: data.name,
        device_type: data.device_type as EnvironmentDeviceCreate["device_type"],
        pin_or_address: data.pin_or_address,
        enabled: data.enabled,
        poll_interval_seconds: data.poll_interval_seconds,
        temperature_unit: data.temperature_unit as EnvironmentDeviceCreate["temperature_unit"],
        notes: data.notes || null,
        target_temperature: data.target_temperature ? parseFloat(data.target_temperature) : null,
        target_humidity: data.target_humidity ? parseFloat(data.target_humidity) : null,
        target_pressure: null,
        temperature_tolerance: data.temperature_tolerance ? parseFloat(data.temperature_tolerance) : 5,
        humidity_tolerance: data.humidity_tolerance ? parseFloat(data.humidity_tolerance) : 10,
        pressure_tolerance: 20,
      };
      const response = await apiClient.POST("/api/v1/environment/devices", {
        body: deviceData,
      });
      if (response.error) {
        const errorDetail = (response.error as { detail?: string })?.detail;
        throw new Error(errorDetail || "Failed to create device");
      }
      return response.data;
    },
    {
      successMessage: "Feedback device added successfully",
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["environment-devices"] });
        setAddModalOpen(false);
        resetForm();
      },
    }
  );

  // Update device mutation
  const updateMutation = useApiMutation(
    async ({ id, data }: { id: number; data: DeviceFormData }) => {
      const updateData: EnvironmentDeviceUpdate = {
        name: data.name,
        device_type: data.device_type as EnvironmentDeviceUpdate["device_type"],
        pin_or_address: data.pin_or_address,
        enabled: data.enabled,
        poll_interval_seconds: data.poll_interval_seconds,
        temperature_unit: data.temperature_unit as EnvironmentDeviceUpdate["temperature_unit"],
        notes: data.notes || null,
        target_temperature: data.target_temperature ? parseFloat(data.target_temperature) : null,
        target_humidity: data.target_humidity ? parseFloat(data.target_humidity) : null,
        target_pressure: null,
        temperature_tolerance: data.temperature_tolerance ? parseFloat(data.temperature_tolerance) : 5,
        humidity_tolerance: data.humidity_tolerance ? parseFloat(data.humidity_tolerance) : 10,
        pressure_tolerance: 20,
      };
      const response = await apiClient.PATCH("/api/v1/environment/devices/{device_id}", {
        params: { path: { device_id: id } },
        body: updateData,
      });
      if (response.error) {
        const errorDetail = (response.error as { detail?: string })?.detail;
        throw new Error(errorDetail || "Failed to update device");
      }
      return response.data;
    },
    {
      successMessage: "Feedback device updated successfully",
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["environment-devices"] });
        setEditDevice(null);
        resetForm();
      },
    }
  );

  // Delete device mutation
  const deleteMutation = useApiMutation(
    async (deviceId: number) => {
      const response = await apiClient.DELETE("/api/v1/environment/devices/{device_id}", {
        params: { path: { device_id: deviceId } },
      });
      if (response.error) {
        const errorDetail = (response.error as { detail?: string })?.detail;
        throw new Error(errorDetail || "Failed to delete device");
      }
    },
    {
      successMessage: "Feedback device deleted successfully",
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["environment-devices"] });
        setDeleteDevice(null);
      },
    }
  );

  // Toggle enabled mutation
  const toggleEnabledMutation = useApiMutation(
    async ({ id, enabled }: { id: number; enabled: boolean }) => {
      const response = await apiClient.PATCH("/api/v1/environment/devices/{device_id}", {
        params: { path: { device_id: id } },
        body: { enabled },
      });
      if (response.error) {
        throw new Error("Failed to update device");
      }
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["environment-devices"] });
      },
    }
  );

  const resetForm = () => {
    setFormData({
      name: "",
      device_type: "dht22",
      pin_or_address: "",
      enabled: true,
      poll_interval_seconds: 10,
      temperature_unit: "C",
      notes: "",
      target_temperature: "",
      target_humidity: "",
      temperature_tolerance: "5",
      humidity_tolerance: "10",
    });
    setFormErrors({});
  };

  const validateForm = (): boolean => {
    const errors: Partial<Record<keyof DeviceFormData, string>> = {};

    if (!formData.name.trim()) {
      errors.name = "Device name is required";
    }

    if (!formData.pin_or_address.trim()) {
      errors.pin_or_address = "Pin or address is required";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleOpenAdd = () => {
    resetForm();
    setAddModalOpen(true);
  };

  const handleOpenEdit = (device: EnvironmentDeviceResponse) => {
    setFormData({
      name: device.name,
      device_type: device.device_type,
      pin_or_address: device.pin_or_address,
      enabled: device.enabled,
      poll_interval_seconds: device.poll_interval_seconds,
      temperature_unit: (device.temperature_unit as "C" | "F") || "C",
      notes: device.notes || "",
      target_temperature: device.target_temperature?.toString() || "",
      target_humidity: device.target_humidity?.toString() || "",
      temperature_tolerance: device.temperature_tolerance?.toString() || "5",
      humidity_tolerance: device.humidity_tolerance?.toString() || "10",
    });
    setFormErrors({});
    setEditDevice(device);
  };

  const handleAddDevice = async () => {
    if (!validateForm()) return;
    await createMutation.mutateAsync(formData);
  };

  const handleEditDevice = async () => {
    if (!editDevice || !validateForm()) return;
    await updateMutation.mutateAsync({ id: editDevice.id, data: formData });
  };

  const handleDeleteDevice = async () => {
    if (!deleteDevice) return;
    await deleteMutation.mutateAsync(deleteDevice.id);
  };

  const handleToggleEnabled = (device: EnvironmentDeviceResponse) => {
    toggleEnabledMutation.mutate({ id: device.id, enabled: !device.enabled });
  };

  const handleChange = (field: keyof DeviceFormData, value: string | boolean | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (formErrors[field]) {
      setFormErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const selectedDeviceType = getDeviceTypeInfo(formData.device_type);

  const renderDeviceForm = (isEdit: boolean) => (
    <div className="device-form">
      <FormField
        label="Device Name"
        type="text"
        value={formData.name}
        onChange={(e) => handleChange("name", e.target.value)}
        error={formErrors.name}
        placeholder="e.g., Chamber Sensor 1"
        required
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
      />

      <FormField
        element="select"
        label="Device Type"
        value={formData.device_type}
        onChange={(e) => handleChange("device_type", e.target.value)}
        required
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
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
        onChange={(e) => handleChange("pin_or_address", e.target.value)}
        error={formErrors.pin_or_address}
        placeholder={selectedDeviceType?.pin_placeholder || ""}
        helperText={`Interface: ${selectedDeviceType?.interface || "GPIO"}`}
        required
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
      />

      <FormField
        label="Poll Interval (seconds)"
        type="number"
        value={formData.poll_interval_seconds.toString()}
        onChange={(e) => handleChange("poll_interval_seconds", parseInt(e.target.value) || 30)}
        helperText="How often to read from this sensor (5-3600 seconds)"
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
      />

      <FormField
        element="select"
        label="Temperature Unit"
        value={formData.temperature_unit}
        onChange={(e) => handleChange("temperature_unit", e.target.value)}
        helperText="Display temperature in Celsius or Fahrenheit"
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
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
          onChange={(e) => handleChange("target_temperature", e.target.value)}
          placeholder="e.g., 22"
          helperText="Leave empty to disable comparison"
          disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
        />
        <FormField
          label="± Tolerance"
          type="number"
          value={formData.temperature_tolerance}
          onChange={(e) => handleChange("temperature_tolerance", e.target.value)}
          placeholder="5"
          helperText="Acceptable range"
          disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
        />
      </div>

      <div className="form-row">
        <FormField
          label="Target Humidity (%)"
          type="number"
          value={formData.target_humidity}
          onChange={(e) => handleChange("target_humidity", e.target.value)}
          placeholder="e.g., 50"
          helperText="Leave empty to disable comparison"
          disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
        />
        <FormField
          label="± Tolerance"
          type="number"
          value={formData.humidity_tolerance}
          onChange={(e) => handleChange("humidity_tolerance", e.target.value)}
          placeholder="10"
          helperText="Acceptable range"
          disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
        />
      </div>

      <FormField
        label="Notes (optional)"
        type="text"
        value={formData.notes}
        onChange={(e) => handleChange("notes", e.target.value)}
        placeholder="e.g., Located in upper left corner"
        disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
      />

      <div className="form-field">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.enabled}
            onChange={(e) => handleChange("enabled", e.target.checked)}
            disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
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
          onClick={() => isEdit ? setEditDevice(null) : setAddModalOpen(false)}
          disabled={isEdit ? updateMutation.isPending : createMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={isEdit ? handleEditDevice : handleAddDevice}
          loading={isEdit ? updateMutation.isPending : createMutation.isPending}
        >
          {isEdit ? "Update Device" : "Add Device"}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="environment-panel">
      {/* Feedback Section */}
      <section className="panel-section">
        <div className="section-header">
          <div>
            <h2>Feedback Devices</h2>
            <p className="section-description">
              Configure sensors for environmental monitoring (temperature, humidity, etc.)
            </p>
          </div>
          <div className="section-actions">
            <Button variant="primary" onClick={handleOpenAdd}>
              Add Device
            </Button>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="panel-loading">
            <div className="loading-spinner"></div>
            <p>Loading devices...</p>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="panel-error">
            <p>Failed to load devices. Please try again.</p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && devices.length === 0 && (
          <div className="panel-empty">
            <div className="empty-icon">🌡️</div>
            <h3>No feedback devices configured</h3>
            <p>Add sensors to monitor environmental conditions</p>
            <Button variant="primary" onClick={handleOpenAdd}>
              Add Device
            </Button>
          </div>
        )}

        {/* Devices list */}
        {!isLoading && !error && devices.length > 0 && (
          <div className="devices-list">
            {devices.map((device) => {
              const typeInfo = getDeviceTypeInfo(device.device_type);
              return (
                <div key={device.id} className="device-card">
                  <div className="device-info">
                    <div className="device-header">
                      <h3>{device.name}</h3>
                      <span className={`device-status ${device.enabled ? "enabled" : "disabled"}`}>
                        {device.enabled ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="device-details">
                      <div className="device-detail">
                        <span className="detail-label">Type:</span>
                        <span className="detail-value">{typeInfo?.name || device.device_type}</span>
                      </div>
                      <div className="device-detail">
                        <span className="detail-label">{typeInfo?.pin_label || "Pin"}:</span>
                        <span className="detail-value">{device.pin_or_address}</span>
                      </div>
                      <div className="device-detail">
                        <span className="detail-label">Poll:</span>
                        <span className="detail-value">{device.poll_interval_seconds}s</span>
                      </div>
                      <div className="device-detail">
                        <span className="detail-label">Temp:</span>
                        <span className="detail-value">{device.temperature_unit === "F" ? "°F" : "°C"}</span>
                      </div>
                    </div>
                    {device.notes && (
                      <div className="device-notes">{device.notes}</div>
                    )}
                  </div>

                  <div className="device-actions">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggleEnabled(device)}
                      disabled={toggleEnabledMutation.isPending}
                    >
                      {device.enabled ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenEdit(device)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setDeleteDevice(device)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Control Section (placeholder for future) */}
      <section className="panel-section">
        <div className="section-header">
          <div>
            <h2>Control Devices</h2>
            <p className="section-description">
              Configure heaters, coolers, and other control devices
            </p>
          </div>
        </div>
        <div className="coming-soon">
          <p>Control device configuration coming soon</p>
        </div>
      </section>

      {/* Add Device Modal */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Add Feedback Device"
        width="md"
      >
        {renderDeviceForm(false)}
      </Modal>

      {/* Edit Device Modal */}
      <Modal
        isOpen={Boolean(editDevice)}
        onClose={() => setEditDevice(null)}
        title="Edit Feedback Device"
        width="md"
      >
        {renderDeviceForm(true)}
      </Modal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(deleteDevice)}
        onClose={() => setDeleteDevice(null)}
        onConfirm={handleDeleteDevice}
        title="Delete Feedback Device"
        message={`Are you sure you want to delete "${deleteDevice?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
