/**
 * Camera add/edit form component
 */

import { useState, useEffect } from "react";
import { FormField } from "../FormField";
import { Button } from "../Button";
import type { components } from "../../types/api";
import "./CameraForm.css";

type CameraResponse = components["schemas"]["CameraResponse"];

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
        disabled={loading || Boolean(camera)} // Disable type change when editing
      >
        <option value="usb">USB Camera</option>
        <option value="csi">CSI Camera</option>
      </FormField>

      <FormField
        label="Device Path"
        type="text"
        value={formData.device_path}
        onChange={(e) => handleChange("device_path", e.target.value)}
        error={errors.device_path}
        placeholder={formData.camera_type === "usb" ? "/dev/video0" : "/dev/video0"}
        helperText={
          formData.camera_type === "usb"
            ? "USB cameras typically use /dev/videoN"
            : "CSI camera path"
        }
        required
        disabled={loading || Boolean(camera)} // Disable path change when editing
      />

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
