/**
 * Cameras management panel with CRUD operations
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useToast } from "../../contexts/ToastContext";
import { Button } from "../Button";
import { Modal } from "../Modal";
import { ConfirmDialog } from "../ConfirmDialog";
import { CameraForm, type CameraFormData } from "./CameraForm";
import type { components } from "../../types/api";
import "./CamerasPanel.css";

type CameraResponse = components["schemas"]["CameraResponse"];
type CameraCreate = components["schemas"]["CameraCreate"];
type CameraUpdate = components["schemas"]["CameraUpdate"];

export function CamerasPanel() {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editCamera, setEditCamera] = useState<CameraResponse | null>(null);
  const [deleteCamera, setDeleteCamera] = useState<CameraResponse | null>(null);
  const [isDiscovering, setIsDiscovering] = useState(false);

  const queryClient = useQueryClient();
  const toast = useToast();

  // Fetch cameras
  const { data: camerasData, isLoading, error } = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/cameras");
      if (response.error) {
        throw new Error("Failed to fetch cameras");
      }
      return response.data;
    },
  });

  const cameras = camerasData?.cameras || [];

  // Create camera mutation
  const createMutation = useMutation({
    mutationFn: async (data: CameraFormData) => {
      const cameraData: CameraCreate = {
        name: data.name,
        device_path: data.device_path,
        camera_type: data.camera_type,
        enabled: data.enabled,
      };
      const response = await apiClient.POST("/api/v1/cameras", {
        body: cameraData,
      });
      if (response.error) {
        throw new Error("Failed to create camera");
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras"] });
      toast.success("Camera added successfully");
      setAddModalOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to add camera");
    },
  });

  // Update camera mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: CameraFormData }) => {
      const updateData: CameraUpdate = {
        name: data.name,
        enabled: data.enabled,
      };
      const response = await apiClient.PATCH("/api/v1/cameras/{camera_id}", {
        params: { path: { camera_id: id } },
        body: updateData,
      });
      if (response.error) {
        throw new Error("Failed to update camera");
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras"] });
      toast.success("Camera updated successfully");
      setEditCamera(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update camera");
    },
  });

  // Delete camera mutation
  const deleteMutation = useMutation({
    mutationFn: async (cameraId: number) => {
      const response = await apiClient.DELETE("/api/v1/cameras/{camera_id}", {
        params: { path: { camera_id: cameraId } },
      });
      if (response.error) {
        throw new Error("Failed to delete camera");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras"] });
      toast.success("Camera deleted successfully");
      setDeleteCamera(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete camera");
    },
  });

  // Toggle camera enabled status
  const toggleEnabledMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
      const response = await apiClient.PATCH("/api/v1/cameras/{camera_id}", {
        params: { path: { camera_id: id } },
        body: { enabled },
      });
      if (response.error) {
        throw new Error("Failed to update camera");
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update camera");
    },
  });

  // Camera discovery (placeholder - would need backend endpoint)
  const handleDiscover = async () => {
    setIsDiscovering(true);
    try {
      // Simulated discovery - in real implementation, call POST /api/v1/cameras/discover
      await new Promise((resolve) => setTimeout(resolve, 1500));
      toast.info("Camera discovery feature coming soon");
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAddCamera = async (data: CameraFormData) => {
    await createMutation.mutateAsync(data);
  };

  const handleEditCamera = async (data: CameraFormData) => {
    if (!editCamera) return;
    await updateMutation.mutateAsync({ id: editCamera.id, data });
  };

  const handleDeleteCamera = async () => {
    if (!deleteCamera) return;
    await deleteMutation.mutateAsync(deleteCamera.id);
  };

  const handleToggleEnabled = (camera: CameraResponse) => {
    toggleEnabledMutation.mutate({ id: camera.id, enabled: !camera.enabled });
  };

  return (
    <div className="cameras-panel">
      <div className="panel-header">
        <div>
          <h1>Camera Management</h1>
          <p className="panel-description">
            Manage your cameras, configure settings, and discover new devices
          </p>
        </div>
        <div className="panel-actions">
          <Button
            variant="outline"
            onClick={handleDiscover}
            loading={isDiscovering}
          >
            Discover Cameras
          </Button>
          <Button variant="primary" onClick={() => setAddModalOpen(true)}>
            Add Camera
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="panel-loading">
          <div className="loading-spinner"></div>
          <p>Loading cameras...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="panel-error">
          <p>Failed to load cameras. Please try again.</p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && cameras.length === 0 && (
        <div className="panel-empty">
          <div className="empty-icon">📷</div>
          <h3>No cameras configured</h3>
          <p>Add your first camera to get started</p>
          <Button variant="primary" onClick={() => setAddModalOpen(true)}>
            Add Camera
          </Button>
        </div>
      )}

      {/* Cameras list */}
      {!isLoading && !error && cameras.length > 0 && (
        <div className="cameras-list">
          {cameras.map((camera) => (
            <div key={camera.id} className="camera-card">
              <div className="camera-info">
                <div className="camera-header">
                  <h3>{camera.name}</h3>
                  <span className={`camera-status ${camera.enabled ? "enabled" : "disabled"}`}>
                    {camera.enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <div className="camera-details">
                  <div className="camera-detail">
                    <span className="detail-label">Type:</span>
                    <span className="detail-value">{camera.camera_type.toUpperCase()}</span>
                  </div>
                  <div className="camera-detail">
                    <span className="detail-label">Device:</span>
                    <span className="detail-value">{camera.device_path}</span>
                  </div>
                </div>
              </div>

              <div className="camera-actions">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleEnabled(camera)}
                  disabled={toggleEnabledMutation.isPending}
                >
                  {camera.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditCamera(camera)}
                >
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setDeleteCamera(camera)}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Camera Modal */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Add Camera"
        width="md"
      >
        <CameraForm
          onSubmit={handleAddCamera}
          onCancel={() => setAddModalOpen(false)}
          loading={createMutation.isPending}
        />
      </Modal>

      {/* Edit Camera Modal */}
      <Modal
        isOpen={Boolean(editCamera)}
        onClose={() => setEditCamera(null)}
        title="Edit Camera"
        width="md"
      >
        <CameraForm
          camera={editCamera}
          onSubmit={handleEditCamera}
          onCancel={() => setEditCamera(null)}
          loading={updateMutation.isPending}
        />
      </Modal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(deleteCamera)}
        onClose={() => setDeleteCamera(null)}
        onConfirm={handleDeleteCamera}
        title="Delete Camera"
        message={`Are you sure you want to delete "${deleteCamera?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
