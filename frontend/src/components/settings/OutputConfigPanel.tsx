/**
 * Output configuration panel
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useToast } from "../../contexts/ToastContext";
import { FormField } from "../FormField";
import { Button } from "../Button";
import type { components } from "../../types/api";
import "./OutputConfigPanel.css";

type OutputConfigResponse = components["schemas"]["OutputConfigResponse"];
type OutputConfigUpdate = components["schemas"]["OutputConfigUpdate"];

interface OutputConfigFormData {
  recording_base_path: string;
  still_base_path: string;
  timelapse_base_path: string;
  retention_days: number;
  max_storage_gb: number;
}

export function OutputConfigPanel() {
  const queryClient = useQueryClient();
  const toast = useToast();

  // Fetch output config
  const { data: configData, isLoading, error } = useQuery({
    queryKey: ["output-config"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/output-config");
      if (response.error) {
        throw new Error("Failed to fetch output configuration");
      }
      return response.data as OutputConfigResponse;
    },
  });

  // Initialize form data from loaded config, or use defaults
  const [formData, setFormData] = useState<OutputConfigFormData>(() => ({
    recording_base_path: "/var/lib/timemachine/recordings",
    still_base_path: "/var/lib/timemachine/stills",
    timelapse_base_path: "/var/lib/timemachine/timelapse",
    retention_days: 7,
    max_storage_gb: 50,
  }));

  const [errors, setErrors] = useState<Partial<Record<keyof OutputConfigFormData, string>>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Update form when data loads
  // eslint-disable-next-line react-compiler/react-compiler
  useEffect(() => {
    if (configData) {
      setFormData({
        recording_base_path: configData.recording_base_path,
        still_base_path: configData.still_base_path,
        timelapse_base_path: configData.timelapse_base_path,
        retention_days: configData.retention_days,
        max_storage_gb: configData.max_storage_gb,
      });
      setHasChanges(false);
    }
  }, [configData]);

  // Update config mutation
  const updateMutation = useMutation({
    mutationFn: async (data: OutputConfigUpdate) => {
      const response = await apiClient.PATCH("/api/v1/output-config", {
        body: data,
      });
      if (response.error) {
        throw new Error("Failed to update configuration");
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["output-config"] });
      toast.success("Output configuration saved successfully");
      setHasChanges(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to save configuration");
    },
  });

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof OutputConfigFormData, string>> = {};

    if (!formData.recording_base_path.trim()) {
      newErrors.recording_base_path = "Recording path is required";
    } else if (!formData.recording_base_path.startsWith("/")) {
      newErrors.recording_base_path = "Path must be absolute (start with /)";
    }

    if (!formData.still_base_path.trim()) {
      newErrors.still_base_path = "Still captures path is required";
    } else if (!formData.still_base_path.startsWith("/")) {
      newErrors.still_base_path = "Path must be absolute (start with /)";
    }

    if (!formData.timelapse_base_path.trim()) {
      newErrors.timelapse_base_path = "Timelapse path is required";
    } else if (!formData.timelapse_base_path.startsWith("/")) {
      newErrors.timelapse_base_path = "Path must be absolute (start with /)";
    }

    if (formData.retention_days < 1) {
      newErrors.retention_days = "Retention must be at least 1 day";
    } else if (formData.retention_days > 365) {
      newErrors.retention_days = "Retention cannot exceed 365 days";
    }

    if (formData.max_storage_gb < 1) {
      newErrors.max_storage_gb = "Storage limit must be at least 1 GB";
    } else if (formData.max_storage_gb > 1000) {
      newErrors.max_storage_gb = "Storage limit cannot exceed 1000 GB";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: keyof OutputConfigFormData, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasChanges(true);
    // Clear error for this field when user types
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const updateData: OutputConfigUpdate = {
      recording_base_path: formData.recording_base_path,
      still_base_path: formData.still_base_path,
      timelapse_base_path: formData.timelapse_base_path,
      retention_days: formData.retention_days,
      max_storage_gb: formData.max_storage_gb,
    };

    await updateMutation.mutateAsync(updateData);
  };

  const handleReset = () => {
    if (configData) {
      setFormData({
        recording_base_path: configData.recording_base_path,
        still_base_path: configData.still_base_path,
        timelapse_base_path: configData.timelapse_base_path,
        retention_days: configData.retention_days,
        max_storage_gb: configData.max_storage_gb,
      });
      setHasChanges(false);
      setErrors({});
    }
  };

  return (
    <div className="output-config-panel">
      <div className="panel-header">
        <div>
          <h1>Output Configuration</h1>
          <p className="panel-description">
            Configure storage paths and retention policies for media files
          </p>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="panel-loading">
          <div className="loading-spinner"></div>
          <p>Loading configuration...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="panel-error">
          <p>Failed to load configuration. Please try again.</p>
        </div>
      )}

      {/* Configuration form */}
      {!isLoading && !error && configData && (
        <form className="config-form" onSubmit={handleSubmit}>
          <div className="form-section">
            <h2 className="section-title">Storage Paths</h2>
            <p className="section-description">
              Configure where media files will be stored. Paths must be absolute.
            </p>

            <FormField
              label="Recording Base Path"
              type="text"
              value={formData.recording_base_path}
              onChange={(e) => handleChange("recording_base_path", e.target.value)}
              error={errors.recording_base_path}
              placeholder="/var/lib/timemachine/recordings"
              helperText="Directory for video recordings"
              required
              disabled={updateMutation.isPending}
            />

            <FormField
              label="Still Captures Path"
              type="text"
              value={formData.still_base_path}
              onChange={(e) => handleChange("still_base_path", e.target.value)}
              error={errors.still_base_path}
              placeholder="/var/lib/timemachine/stills"
              helperText="Directory for still image captures"
              required
              disabled={updateMutation.isPending}
            />

            <FormField
              label="Timelapse Path"
              type="text"
              value={formData.timelapse_base_path}
              onChange={(e) => handleChange("timelapse_base_path", e.target.value)}
              error={errors.timelapse_base_path}
              placeholder="/var/lib/timemachine/timelapse"
              helperText="Directory for timelapse videos"
              required
              disabled={updateMutation.isPending}
            />
          </div>

          <div className="form-section">
            <h2 className="section-title">Retention & Storage</h2>
            <p className="section-description">
              Configure how long to keep files and maximum storage usage.
            </p>

            <FormField
              label="Retention Days"
              type="number"
              value={formData.retention_days}
              onChange={(e) => handleChange("retention_days", parseInt(e.target.value) || 0)}
              error={errors.retention_days}
              min={1}
              max={365}
              helperText="Number of days to keep recordings (1-365)"
              required
              disabled={updateMutation.isPending}
            />

            <FormField
              label="Maximum Storage (GB)"
              type="number"
              value={formData.max_storage_gb}
              onChange={(e) => handleChange("max_storage_gb", parseInt(e.target.value) || 0)}
              error={errors.max_storage_gb}
              min={1}
              max={1000}
              helperText="Maximum storage usage in gigabytes (1-1000)"
              required
              disabled={updateMutation.isPending}
            />
          </div>

          <div className="form-actions">
            <Button
              type="button"
              variant="secondary"
              onClick={handleReset}
              disabled={!hasChanges || updateMutation.isPending}
            >
              Reset
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={updateMutation.isPending}
              disabled={!hasChanges}
            >
              Save Configuration
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
