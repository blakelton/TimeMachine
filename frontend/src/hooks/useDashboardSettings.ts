/**
 * Hook for fetching dashboard preview settings from output config.
 *
 * Returns the dashboard_preview_enabled and dashboard_preview_fps settings
 * that control whether live previews are shown on the dashboard.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

export interface DashboardPreviewSettings {
  enabled: boolean;
  fps: number;
}

interface UseDashboardSettingsResult {
  settings: DashboardPreviewSettings;
  isLoading: boolean;
  isError: boolean;
}

/**
 * Fetch dashboard preview settings from output config.
 *
 * @example
 * ```tsx
 * const { settings } = useDashboardSettings();
 * if (settings.enabled) {
 *   // Show live previews at settings.fps framerate
 * }
 * ```
 */
export function useDashboardSettings(): UseDashboardSettingsResult {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["outputConfig"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/output-config");
      if (error || !data) {
        throw new Error("Failed to fetch output config");
      }
      return data;
    },
    staleTime: 60000, // Settings don't change often - cache for 1 minute
    retry: 2,
  });

  return {
    settings: {
      enabled: data?.dashboard_preview_enabled ?? true,
      fps: data?.dashboard_preview_fps ?? 10,
    },
    isLoading,
    isError,
  };
}
