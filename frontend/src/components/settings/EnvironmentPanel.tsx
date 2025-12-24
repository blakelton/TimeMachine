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
import {
  EnvironmentDeviceForm,
  EnvironmentDeviceList,
  type DeviceFormData
} from "../environment";
import type { components } from "../../types/api";
import "./EnvironmentPanel.css";

type EnvironmentDeviceResponse = components["schemas"]["EnvironmentDeviceResponse"];
type EnvironmentDeviceCreate = components["schemas"]["EnvironmentDeviceCreate"];
type EnvironmentDeviceUpdate = components["schemas"]["EnvironmentDeviceUpdate"];

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

        <EnvironmentDeviceList
          devices={devices}
          deviceTypes={deviceTypes}
          isLoading={isLoading}
          error={error}
          onAddDevice={handleOpenAdd}
          onToggleEnabled={handleToggleEnabled}
          onEditDevice={handleOpenEdit}
          onDeleteDevice={setDeleteDevice}
          isToggling={toggleEnabledMutation.isPending}
        />
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
        <EnvironmentDeviceForm
          formData={formData}
          formErrors={formErrors}
          deviceTypes={deviceTypes}
          isEdit={false}
          isPending={createMutation.isPending}
          onChange={handleChange}
          onSubmit={handleAddDevice}
          onCancel={() => setAddModalOpen(false)}
        />
      </Modal>

      {/* Edit Device Modal */}
      <Modal
        isOpen={Boolean(editDevice)}
        onClose={() => setEditDevice(null)}
        title="Edit Feedback Device"
        width="md"
      >
        <EnvironmentDeviceForm
          formData={formData}
          formErrors={formErrors}
          deviceTypes={deviceTypes}
          isEdit={true}
          isPending={updateMutation.isPending}
          onChange={handleChange}
          onSubmit={handleEditDevice}
          onCancel={() => setEditDevice(null)}
        />
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
