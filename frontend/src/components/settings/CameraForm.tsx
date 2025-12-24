/**
 * Camera add/edit form component
 */

import { useState, useEffect } from "react";
import { FormField } from "../FormField";
import { Button } from "../Button";
import type { components } from "../../types/api";
import "./CameraForm.css";

type CameraResponse = components["schemas"]["CameraResponse"];
type DiscoveredCameraResponse = components["schemas"]["DiscoveredCameraResponse"];

interface CameraFormProps {
  camera?: CameraResponse | null;
  onSubmit: (data: CameraFormData) => void | Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export interface CameraFormData {
  name: string;
  device_path: string;
  camera_type: "csi" | "usb";
  enabled: boolean;
}

export function CameraForm({
  camera,
  onSubmit,
  onCancel,
  loading = false,
}: CameraFormProps) {
  // Initialize form data with camera values if editing, otherwise use defaults
  const [formData, setFormData] = useState<CameraFormData>(() => {
    if (camera) {
      return {
        name: camera.name,
        device_path: camera.device_path,
        camera_type: camera.camera_type as "csi" | "usb",
        enabled: camera.enabled,
      };
    }
    return {
      name: "",
      device_path: "",
      camera_type: "usb",
      enabled: true,
    };
  });

  const [errors, setErrors] = useState<Partial<Record<keyof CameraFormData, string>>>({});
  const [discoveredCameras, setDiscoveredCameras] = useState<DiscoveredCameraResponse[]>([]);
  const [discoveringCameras, setDiscoveringCameras] = useState(false);

  // Discover available cameras when camera type changes
  // Also runs in edit mode to show available options (including current device)
  useEffect(() => {
    if (formData.camera_type) {
      const discoverCameras = async () => {
        setDiscoveringCameras(true);
        setDiscoveredCameras([]); // Clear previous results
        try {
          // Call discovery endpoint with camera_type as query parameter
          const url = `/api/v1/cameras/discover?camera_type=${formData.camera_type}`;
          const response = await fetch(url, { method: "POST" });

          if (response.ok) {
            let data: DiscoveredCameraResponse[] = await response.json();

            // When editing, add the current camera's device to the list if not already present
            // (discovery excludes already-configured cameras)
            if (camera && !data.some(d => d.device_path === camera.device_path)) {
              data = [
                {
                  name: camera.name,
                  device_path: camera.device_path,
                  camera_type: camera.camera_type,
                  hardware_id: null,
                  capabilities: null,
                },
                ...data,
              ];
            }

            setDiscoveredCameras(data);
            // Auto-select first camera if available and device path is empty or "custom" (only when adding)
            if (!camera && data.length > 0 && (!formData.device_path || formData.device_path === "custom")) {
              setFormData((prev) => ({
                ...prev,
                device_path: data[0].device_path,
                name: prev.name || data[0].name,
              }));
            }
          } else {
            console.error("Camera discovery failed:", response.status, response.statusText);
          }
        } catch (err) {
          console.error("Failed to discover cameras:", err);
        } finally {
          setDiscoveringCameras(false);
        }
      };
      discoverCameras();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.camera_type]); // Only trigger on camera_type change

  // Update form when camera prop changes (for edit mode)
  // eslint-disable-next-line react-compiler/react-compiler
  useEffect(() => {
    if (camera) {
      setFormData({
        name: camera.name,
        device_path: camera.device_path,
        camera_type: camera.camera_type as "csi" | "usb",
        enabled: camera.enabled,
      });
    }
  }, [camera]);

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof CameraFormData, string>> = {};

    if (!formData.name.trim()) {
      newErrors.name = "Camera name is required";
    }

    if (!formData.device_path.trim()) {
      newErrors.device_path = "Device path is required";
    } else if (formData.camera_type === "usb" && !formData.device_path.match(/^\/dev\/video\d+$/)) {
      newErrors.device_path = "USB camera path must be in format /dev/videoN (e.g., /dev/video0)";
    }

    if (!formData.camera_type) {
      newErrors.camera_type = "Camera type is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    await onSubmit(formData);
  };

  const handleChange = (field: keyof CameraFormData, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user types
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <form className="camera-form" onSubmit={handleSubmit}>
      <FormField
        label="Camera Name"
        type="text"
        value={formData.name}
        onChange={(e) => handleChange("name", e.target.value)}
        error={errors.name}
        placeholder="e.g., Main Camera"
        required
        disabled={loading}
      />

      <FormField
        element="select"
        label="Camera Type"
        value={formData.camera_type}
        onChange={(e) => handleChange("camera_type", e.target.value)}
        error={errors.camera_type}
        required
        disabled={loading}
      >
        <option value="usb">USB Camera</option>
        <option value="csi">CSI Camera</option>
      </FormField>

      <FormField
        element="select"
        label="Device Path"
        value={formData.device_path}
        onChange={(e) => handleChange("device_path", e.target.value)}
        error={errors.device_path}
        helperText={
          discoveringCameras
            ? "Discovering cameras..."
            : discoveredCameras.length > 0
            ? "Select a detected camera or choose Custom to enter manually"
            : "No cameras detected - enter path manually"
        }
        required
        disabled={loading || discoveringCameras}
      >
        {discoveredCameras.length === 0 && !discoveringCameras && (
          <option value="">-- No cameras detected --</option>
        )}
        {discoveringCameras && (
          <option value="">-- Discovering cameras... --</option>
        )}
        {discoveredCameras.map((cam) => (
          <option key={cam.device_path} value={cam.device_path}>
            {cam.name} ({cam.device_path}) - {cam.camera_type.toUpperCase()}
          </option>
        ))}
        <option value="custom">Custom (enter manually)</option>
      </FormField>

      {formData.device_path === "custom" && (
        <FormField
          label="Custom Device Path"
          type="text"
          value=""
          onChange={(e) => {
            const newPath = e.target.value;
            setFormData((prev) => ({ ...prev, device_path: newPath || "custom" }));
            if (errors.device_path) {
              setErrors((prev) => ({ ...prev, device_path: undefined }));
            }
          }}
          error={errors.device_path}
          placeholder={formData.camera_type === "usb" ? "/dev/video0" : "/dev/video10"}
          helperText={
            formData.camera_type === "usb"
              ? "USB cameras typically use /dev/videoN"
              : "CSI cameras typically use /dev/video10 or higher"
          }
          required
          disabled={loading}
        />
      )}

      <div className="form-field">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={formData.enabled}
            onChange={(e) => handleChange("enabled", e.target.checked)}
            disabled={loading}
          />
          <span>Enable camera</span>
        </label>
        <div className="form-helper">
          Camera will be available for recording when enabled
        </div>
      </div>

      <div className="form-actions">
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={loading}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          loading={loading}
        >
          {camera ? "Update Camera" : "Add Camera"}
        </Button>
      </div>
    </form>
  );
}
