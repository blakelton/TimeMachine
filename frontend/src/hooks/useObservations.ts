/**
 * Hook for fetching and managing observations data.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "../contexts/ToastContext";

/**
 * Completed observation data from the API
 */
export interface CompletedObservation {
  id: number;
  camera_id: number;
  camera_name: string;
  observation_type: "timelapse" | "recording" | "still";
  status: "completed" | "stopped" | "failed";
  started_at: string;
  completed_at: string | null;
  duration_seconds: number;
  frame_count: number | null;
  size_bytes: number;
  size_display: string;
  notes: string | null;
  thumbnail_url: string;
  media_url: string;
}

export interface ObservationListResponse {
  observations: CompletedObservation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ObservationFilters {
  camera_id?: number;
  observation_type?: "timelapse" | "recording" | "still";
  limit?: number;
  offset?: number;
}

/**
 * Fetch completed observations with optional filters
 */
export function useObservations(filters: ObservationFilters = {}) {
  const { camera_id, observation_type, limit = 50, offset = 0 } = filters;

  return useQuery({
    queryKey: ["observations", "completed", camera_id, observation_type, limit, offset],
    queryFn: async (): Promise<ObservationListResponse> => {
      // Build query params
      const params: Record<string, string> = {
        limit: String(limit),
        offset: String(offset),
      };
      if (camera_id !== undefined) {
        params.camera_id = String(camera_id);
      }
      if (observation_type) {
        params.observation_type = observation_type;
      }

      const queryString = new URLSearchParams(params).toString();
      const response = await fetch(`/api/v1/observations/completed?${queryString}`);

      if (!response.ok) {
        throw new Error("Failed to fetch observations");
      }

      return response.json();
    },
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Delete an observation
 */
export function useDeleteObservation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: async (observationId: number) => {
      const response = await fetch(`/api/v1/observations/${observationId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Failed to delete observation");
      }

      return response.json();
    },
    onSuccess: () => {
      toast.success("Observation deleted successfully");
      // Invalidate observations list
      queryClient.invalidateQueries({ queryKey: ["observations"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete observation");
    },
  });
}

/**
 * Get thumbnail URL for an observation
 */
export function getThumbnailUrl(observationId: number): string {
  return `/api/v1/observations/${observationId}/thumbnail`;
}

/**
 * Get media URL for an observation
 */
export function getMediaUrl(observationId: number): string {
  return `/api/v1/observations/${observationId}/media`;
}

/**
 * Batch delete multiple observations
 */
export function useBatchDeleteObservations() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: async (observationIds: number[]) => {
      const params = new URLSearchParams();
      observationIds.forEach((id) => params.append("observation_ids", String(id)));

      const response = await fetch(`/api/v1/observations/batch-delete?${params.toString()}`, {
        method: "POST",
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Failed to delete observations");
      }

      return response.json();
    },
    onSuccess: (data) => {
      const { summary } = data;
      if (summary.deleted_count > 0) {
        toast.success(`Deleted ${summary.deleted_count} observation${summary.deleted_count !== 1 ? "s" : ""}`);
      }
      if (summary.skipped_count > 0) {
        toast.warning(`Skipped ${summary.skipped_count} observation${summary.skipped_count !== 1 ? "s" : ""}`);
      }
      // Invalidate observations list
      queryClient.invalidateQueries({ queryKey: ["observations"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete observations");
    },
  });
}
