/**
 * Hook for fetching camera dashboard data with live preview states.
 *
 * Polls the batch dashboard endpoint for efficient data fetching
 * of all cameras in a single request. Optionally auto-starts
 * preview streams based on dashboard settings.
 *
 * Includes a watchdog mechanism that:
 * - Retries starting previews that fail to come up
 * - Uses exponential backoff (2s, 4s, 8s, 16s, max 30s)
 * - Resets retry state when preview starts successfully
 */

import { useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { components } from "../types/api";
import type { DashboardPreviewSettings } from "./useDashboardSettings";

export type CameraDashboardItem = components["schemas"]["CameraDashboardItem"];
export type CameraDashboardObservation = components["schemas"]["CameraDashboardObservation"];
export type CameraDashboardResponse = components["schemas"]["CameraDashboardResponse"];

// Retry configuration
const INITIAL_RETRY_DELAY = 2000; // 2 seconds
const MAX_RETRY_DELAY = 30000; // 30 seconds
const MAX_RETRIES = 10; // Give up after 10 retries

interface CameraRetryState {
  retryCount: number;
  nextRetryTime: number; // timestamp when next retry is allowed
}

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
 * Calculate next retry delay with exponential backoff.
 */
function getRetryDelay(retryCount: number): number {
  const delay = INITIAL_RETRY_DELAY * Math.pow(2, retryCount);
  return Math.min(delay, MAX_RETRY_DELAY);
}

/**
 * Fetch camera dashboard data for all cameras.
 *
 * Returns preview states, active observations, and progress info
 * in a single batch request to avoid N+1 API calls.
 *
 * When previewSettings is provided and enabled, automatically starts
 * preview streams for idle cameras. Includes watchdog retry logic
 * with exponential backoff for cameras that fail to start.
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

  // Track retry state per camera with exponential backoff
  const retryStateRef = useRef<Map<number, CameraRetryState>>(new Map());

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

  // Try to start preview for a camera, handling retries with exponential backoff
  const tryStartPreview = useCallback(async (
    cameraId: number,
    fps: number
  ): Promise<void> => {
    const now = Date.now();
    const retryState = retryStateRef.current.get(cameraId);

    // Check if we should wait before retrying
    if (retryState) {
      // Already at max retries - give up
      if (retryState.retryCount >= MAX_RETRIES) {
        return;
      }
      // Not yet time for next retry
      if (now < retryState.nextRetryTime) {
        return;
      }
    }

    // Attempt to start preview
    const success = await startCameraPreview(cameraId, fps);

    if (success) {
      // Success - remove from retry tracking
      retryStateRef.current.delete(cameraId);
    } else {
      // Failed - update retry state with backoff
      const currentRetryCount = retryState?.retryCount ?? 0;
      const newRetryCount = currentRetryCount + 1;
      const delay = getRetryDelay(newRetryCount);

      retryStateRef.current.set(cameraId, {
        retryCount: newRetryCount,
        nextRetryTime: now + delay,
      });
    }
  }, []);

  // Watchdog effect - runs on each data update to check camera states
  useEffect(() => {
    // Only run if settings are provided and previews are enabled
    if (!previewSettings?.enabled || !data?.cameras || previewSettings.fps === 0) {
      return;
    }

    const cameras = data.cameras ?? [];

    // Process each camera
    const processCamera = async (camera: CameraDashboardItem) => {
      // Skip if camera is disabled or has active observation
      if (!camera.enabled || camera.has_active_observation) {
        // Clear retry state - camera is legitimately not available
        retryStateRef.current.delete(camera.camera_id);
        return;
      }

      // If preview is running, clear any retry state (success!)
      if (camera.preview_state === "running") {
        retryStateRef.current.delete(camera.camera_id);
        return;
      }

      // Preview is idle or error - try to start it
      if (camera.preview_state === "idle" || camera.preview_state === "error") {
        await tryStartPreview(camera.camera_id, previewSettings.fps);
      }
    };

    // Process cameras sequentially to avoid overwhelming the backend
    const processAllCameras = async () => {
      for (const camera of cameras) {
        await processCamera(camera);
      }
    };

    processAllCameras();
  }, [data?.cameras, previewSettings?.enabled, previewSettings?.fps, tryStartPreview]);

  // Reset retry state when settings are disabled
  useEffect(() => {
    if (!previewSettings?.enabled) {
      retryStateRef.current.clear();
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
