/**
 * Output configuration panel
 */

import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useApiMutation } from "../../hooks/useApiMutation";
import { FormField } from "../FormField";
import { Button } from "../Button";
import type { components } from "../../types/api";
import "./OutputConfigPanel.css";

type OutputConfigResponse = components["schemas"]["OutputConfigResponse"];
type OutputConfigUpdate = components["schemas"]["OutputConfigUpdate"];

interface OutputConfigFormData {
  recordings_path: string;
  stills_path: string;
  timelapse_path: string;
  retention_days: number;
  retention_max_gb: number;
}

export function OutputConfigPanel() {
  const queryClient = useQueryClient();

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
    recordings_path: "/var/lib/timemachine/media/recordings",
    stills_path: "/var/lib/timemachine/media/stills",
    timelapse_path: "/var/lib/timemachine/media/timelapse",
    retention_days: 30,
    retention_max_gb: 50,
  }));

  const [errors, setErrors] = useState<Partial<Record<keyof OutputConfigFormData, string>>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Update form when data loads
  // eslint-disable-next-line react-compiler/react-compiler
  useEffect(() => {
    if (configData) {
      setFormData({
        recordings_path: configData.recordings_path,
        stills_path: configData.stills_path,
        timelapse_path: configData.timelapse_path,
        retention_days: configData.retention_days,
        retention_max_gb: configData.retention_max_gb,
      });
      setHasChanges(false);
    }
  }, [configData]);

  // Update config mutation using custom hook
  const updateMutation = useApiMutation(
    async (data: OutputConfigUpdate) => {
      const response = await apiClient.PATCH("/api/v1/output-config", {
        body: data,
      });
      if (response.error) {
        throw new Error("Failed to update configuration");
      }
      return response.data;
    },
    {
      successMessage: "Output configuration saved successfully",
      errorMessage: "Failed to save configuration",
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["output-config"] });
        setHasChanges(false);
      },
    }
  );

  /**
   * Validation rules configuration.
   * Declarative approach reduces cyclomatic complexity from 11 to ~2.
   */
  const validationRules = [
    {
      field: "recordings_path" as keyof OutputConfigFormData,
      validators: [
        {
          check: (value: string | number) => !String(value).trim(),
          error: "Recording path is required",
        },
        {
          check: (value: string | number) => !String(value).startsWith("/"),
          error: "Path must be absolute (start with /)",
        },
      ],
    },
    {
      field: "stills_path" as keyof OutputConfigFormData,
      validators: [
        {
          check: (value: string | number) => !String(value).trim(),
          error: "Still captures path is required",
        },
        {
          check: (value: string | number) => !String(value).startsWith("/"),
          error: "Path must be absolute (start with /)",
        },
      ],
    },
    {
      field: "timelapse_path" as keyof OutputConfigFormData,
      validators: [
        {
          check: (value: string | number) => !String(value).trim(),
          error: "Timelapse path is required",
        },
        {
          check: (value: string | number) => !String(value).startsWith("/"),
          error: "Path must be absolute (start with /)",
        },
      ],
    },
    {
      field: "retention_days" as keyof OutputConfigFormData,
      validators: [
        {
          check: (value: string | number) => Number(value) < 1,
          error: "Retention must be at least 1 day",
        },
        {
          check: (value: string | number) => Number(value) > 365,
          error: "Retention cannot exceed 365 days",
        },
      ],
    },
    {
      field: "retention_max_gb" as keyof OutputConfigFormData,
      validators: [
        {
          check: (value: string | number) => Number(value) < 1,
          error: "Storage limit must be at least 1 GB",
        },
        {
          check: (value: string | number) => Number(value) > 1000,
          error: "Storage limit cannot exceed 1000 GB",
        },
      ],
    },
  ];

  /**
   * Validates form data using declarative validation rules.
   * This approach reduces cyclomatic complexity and improves maintainability.
   *
   * @returns true if validation passes, false otherwise
   */
  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof OutputConfigFormData, string>> = {};

    for (const rule of validationRules) {
      const value = formData[rule.field];

      for (const validator of rule.validators) {
        if (validator.check(value)) {
          newErrors[rule.field] = validator.error;
          break; // Stop at first error for this field
        }
      }
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
      recordings_path: formData.recordings_path,
      stills_path: formData.stills_path,
      timelapse_path: formData.timelapse_path,
      retention_days: formData.retention_days,
      retention_max_gb: formData.retention_max_gb,
    };

    await updateMutation.mutateAsync(updateData);
  };

  const handleReset = () => {
    if (configData) {
      setFormData({
        recordings_path: configData.recordings_path,
        stills_path: configData.stills_path,
        timelapse_path: configData.timelapse_path,
        retention_days: configData.retention_days,
        retention_max_gb: configData.retention_max_gb,
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
              label="Recordings Path"
              type="text"
              value={formData.recordings_path}
              onChange={(e) => handleChange("recordings_path", e.target.value)}
              error={errors.recordings_path}
              placeholder="/var/lib/timemachine/media/recordings"
              helperText="Directory for video recordings"
              required
              disabled={updateMutation.isPending}
            />

            <FormField
              label="Stills Path"
              type="text"
              value={formData.stills_path}
              onChange={(e) => handleChange("stills_path", e.target.value)}
              error={errors.stills_path}
              placeholder="/var/lib/timemachine/media/stills"
              helperText="Directory for still image captures"
              required
              disabled={updateMutation.isPending}
            />

            <FormField
              label="Timelapse Path"
              type="text"
              value={formData.timelapse_path}
              onChange={(e) => handleChange("timelapse_path", e.target.value)}
              error={errors.timelapse_path}
              placeholder="/var/lib/timemachine/media/timelapse"
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
              value={formData.retention_max_gb}
              onChange={(e) => handleChange("retention_max_gb", parseInt(e.target.value) || 0)}
              error={errors.retention_max_gb}
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
