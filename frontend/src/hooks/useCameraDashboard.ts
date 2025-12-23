/**
 * Hook for fetching camera dashboard data with live preview states.
 *
 * Polls the batch dashboard endpoint for efficient data fetching
 * of all cameras in a single request. Optionally auto-starts
 * preview streams based on dashboard settings.
 */

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { components } from "../types/api";
import type { DashboardPreviewSettings } from "./useDashboardSettings";

export type CameraDashboardItem = components["schemas"]["CameraDashboardItem"];
export type CameraDashboardObservation = components["schemas"]["CameraDashboardObservation"];
export type CameraDashboardResponse = components["schemas"]["CameraDashboardResponse"];

interface UseCameraDashboardOptions {
  /**
   * Polling interval in milliseconds.
   * Default: 3000ms (3 seconds)
   */
  refetchInterval?: number;
  /**
   * Whether to enable automatic refetching.
   * Default: true
   */
  enabled?: boolean;
  /**
   * Dashboard preview settings from output config.
   * When provided and enabled, auto-starts preview streams.
   */
  previewSettings?: DashboardPreviewSettings;
}

interface UseCameraDashboardResult {
  cameras: CameraDashboardItem[];
  timestamp: string | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Start preview for a camera.
 * Returns true if successful, false otherwise.
 */
async function startCameraPreview(cameraId: number, fps: number): Promise<boolean> {
  try {
    const { error } = await apiClient.POST("/api/v1/cameras/{camera_id}/preview/start", {
      params: {
        path: { camera_id: cameraId },
        query: { fps },
      },
    });
    return !error;
  } catch {
    return false;
  }
}

/**
 * Fetch camera dashboard data for all cameras.
 *
 * Returns preview states, active observations, and progress info
 * in a single batch request to avoid N+1 API calls.
 *
 * When previewSettings is provided and enabled, automatically starts
 * preview streams for idle cameras.
 *
 * @example
 * ```tsx
 * const { settings } = useDashboardSettings();
 * const { cameras, isLoading } = useCameraDashboard({
 *   previewSettings: settings,
 * });
 *
 * return cameras.map(camera => (
 *   <CameraPreviewCard key={camera.camera_id} camera={camera} />
 * ));
 * ```
 */
export function useCameraDashboard(
  options: UseCameraDashboardOptions = {}
): UseCameraDashboardResult {
  const { refetchInterval = 3000, enabled = true, previewSettings } = options;

  // Track cameras we've already tried to start previews for
  const startedPreviewsRef = useRef<Set<number>>(new Set());

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["cameraDashboard"],
    queryFn: async (): Promise<CameraDashboardResponse> => {
      const { data, error } = await apiClient.GET("/api/v1/cameras/dashboard");
      if (error) {
        const message = (error as { detail?: string })?.detail || "Unknown error";
        throw new Error(`Failed to fetch camera dashboard: ${message}`);
      }
      if (!data) {
        throw new Error("Failed to fetch camera dashboard: No data returned");
      }
      return data;
    },
    refetchInterval,
    enabled,
    retry: 2,
    staleTime: 1000, // Consider data stale after 1 second
  });

  // Auto-start previews when dashboard loads (if settings enabled)
  useEffect(() => {
    // Only run if settings are provided and previews are enabled
    if (!previewSettings?.enabled || !data?.cameras || previewSettings.fps === 0) {
      return;
    }

    // Start previews for cameras that are idle and don't have active observations
    const cameras = data.cameras ?? [];
    const startPreviews = async () => {
      for (const camera of cameras) {
        // Skip if:
        // - Camera is disabled
        // - Preview is already running or has error
        // - Camera has an active observation (uses the camera)
        // - We already tried to start this camera's preview
        if (
          !camera.enabled ||
          camera.preview_state !== "idle" ||
          camera.has_active_observation ||
          startedPreviewsRef.current.has(camera.camera_id)
        ) {
          continue;
        }

        // Mark as attempted
        startedPreviewsRef.current.add(camera.camera_id);

        // Start preview with configured FPS
        await startCameraPreview(camera.camera_id, previewSettings.fps);
      }
    };

    startPreviews();
  }, [data?.cameras, previewSettings?.enabled, previewSettings?.fps]);

  // Reset started previews when settings change
  useEffect(() => {
    if (!previewSettings?.enabled) {
      startedPreviewsRef.current.clear();
    }
  }, [previewSettings?.enabled]);

  return {
    cameras: data?.cameras ?? [],
    timestamp: data?.timestamp ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
  };
}
