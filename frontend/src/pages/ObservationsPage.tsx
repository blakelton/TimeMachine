/**
 * Observations browser page - displays completed captures, recordings, and timelapses
 */

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { ObservationGrid, MediaViewer, BatchActionBar, downloadMultipleFiles } from "../components/observations";
import { useObservations, useBatchDeleteObservations, type CompletedObservation } from "../hooks/useObservations";
import { useToast } from "../contexts/ToastContext";
import "./ObservationsPage.css";

type ObservationType = "all" | "timelapse" | "recording" | "still";

interface Camera {
  id: number;
  name: string;
}

export function ObservationsPage() {
  const [selectedType, setSelectedType] = useState<ObservationType>("all");
  const [selectedCamera, setSelectedCamera] = useState<number | undefined>(undefined);
  const [viewingObservation, setViewingObservation] = useState<CompletedObservation | null>(null);
  const [viewingIndex, setViewingIndex] = useState(0);

  // Batch selection state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isDownloading, setIsDownloading] = useState(false);

  const toast = useToast();
  const batchDeleteMutation = useBatchDeleteObservations();

  // Fetch cameras for filter dropdown
  const { data: camerasData } = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await apiClient.GET("/api/v1/cameras");
      if (response.error) throw new Error("Failed to fetch cameras");
      return response.data;
    },
    staleTime: 60000,
  });

  const cameras: Camera[] = camerasData?.cameras || [];

  // Fetch observations with filters
  const { data, isLoading, error } = useObservations({
    camera_id: selectedCamera,
    observation_type: selectedType === "all" ? undefined : selectedType,
    limit: 100,
  });

  const observations = data?.observations || [];

  // Handle observation selection
  const handleSelect = useCallback((observation: CompletedObservation, index: number) => {
    setViewingObservation(observation);
    setViewingIndex(index);
  }, []);

  // Handle navigation in viewer
  const handleNavigate = useCallback((index: number) => {
    if (index >= 0 && index < observations.length) {
      setViewingObservation(observations[index]);
      setViewingIndex(index);
    }
  }, [observations]);

  // Close viewer
  const handleClose = useCallback(() => {
    setViewingObservation(null);
  }, []);

  // Batch selection handlers
  const handleToggleSelect = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      // Enable selection mode when first item is selected
      if (next.size > 0 && !selectionMode) {
        setSelectionMode(true);
      }
      // Exit selection mode when all items are deselected
      if (next.size === 0) {
        setSelectionMode(false);
      }
      return next;
    });
  }, [selectionMode]);

  const handleSelectAll = useCallback(() => {
    setSelectedIds(new Set(observations.map((o) => o.id)));
    setSelectionMode(true);
  }, [observations]);

  const handleDeselectAll = useCallback(() => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  }, []);

  const handleBatchDelete = useCallback(async () => {
    const ids = Array.from(selectedIds);
    await batchDeleteMutation.mutateAsync(ids);
    setSelectedIds(new Set());
    setSelectionMode(false);
  }, [selectedIds, batchDeleteMutation]);

  const handleBatchDownload = useCallback(async () => {
    const ids = Array.from(selectedIds);
    setIsDownloading(true);
    try {
      await downloadMultipleFiles(ids);
      toast.success(`Started download of ${ids.length} file${ids.length !== 1 ? "s" : ""}`);
    } catch (error) {
      toast.error("Failed to download files");
    } finally {
      setIsDownloading(false);
    }
  }, [selectedIds, toast]);

  // Toggle selection mode with long press or button
  const handleToggleSelectionMode = useCallback(() => {
    if (selectionMode) {
      setSelectedIds(new Set());
      setSelectionMode(false);
    } else {
      setSelectionMode(true);
    }
  }, [selectionMode]);

  return (
    <div className="observations-page">
      <div className="observations-page__header">
        <div className="observations-page__title">
          <h1>Observations</h1>
          {data && (
            <span className="observations-page__count">
              {data.total} {data.total === 1 ? "observation" : "observations"}
            </span>
          )}
        </div>

        <div className="observations-page__filters">
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as ObservationType)}
            className="observations-page__filter"
          >
            <option value="all">All Types</option>
            <option value="timelapse">Timelapse</option>
            <option value="recording">Recording</option>
            <option value="still">Still</option>
          </select>

          <select
            value={selectedCamera ?? ""}
            onChange={(e) => setSelectedCamera(e.target.value ? Number(e.target.value) : undefined)}
            className="observations-page__filter"
          >
            <option value="">All Cameras</option>
            {cameras.map((camera) => (
              <option key={camera.id} value={camera.id}>
                {camera.name}
              </option>
            ))}
          </select>

          {observations.length > 0 && !selectionMode && (
            <button
              className="observations-page__select-btn"
              onClick={handleToggleSelectionMode}
            >
              Select Multiple
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="observations-page__error">
          Failed to load observations. Please try again.
        </div>
      )}

      {selectionMode && (
        <BatchActionBar
          selectedCount={selectedIds.size}
          totalCount={observations.length}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          onDelete={handleBatchDelete}
          onDownload={handleBatchDownload}
          isDeleting={batchDeleteMutation.isPending}
          isDownloading={isDownloading}
          selectedIds={selectedIds}
        />
      )}

      <div className="observations-page__content">
        <ObservationGrid
          observations={observations}
          onSelect={handleSelect}
          isLoading={isLoading}
          emptyMessage={
            selectedType !== "all" || selectedCamera
              ? "No observations match the selected filters"
              : "No observations yet. Start a recording or timelapse to see them here."
          }
          selectionMode={selectionMode}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
        />
      </div>

      {viewingObservation && (
        <MediaViewer
          observation={viewingObservation}
          observations={observations}
          currentIndex={viewingIndex}
          onClose={handleClose}
          onNavigate={handleNavigate}
        />
      )}
    </div>
  );
}
