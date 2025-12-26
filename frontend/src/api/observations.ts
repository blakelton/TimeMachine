/**
 * Typed API wrappers for observation endpoints.
 *
 * These wrappers provide proper TypeScript types and eliminate the need for
 * `as any` casts when calling path-parameterized endpoints.
 */

import { apiClient } from "./client";

/**
 * Start a new observation (timelapse or recording).
 */
export async function startObservation(request: {
  camera_id: number;
  observation_type: "timelapse" | "recording";
  timelapse_config?: {
    interval_value: number;
    interval_unit: "seconds" | "minutes" | "hours";
    end_mode: "datetime" | "duration";
    end_datetime?: string | null;
    duration_value?: number | null;
    duration_unit?: ("seconds" | "minutes" | "hours") | null;
    output_fps: number;
    resolution_width: number;
    resolution_height: number;
    quality: number;
  } | null;
  recording_config?: {
    end_mode: "datetime" | "duration" | "manual";
    end_datetime?: string | null;
    duration_value?: number | null;
    duration_unit?: ("seconds" | "minutes" | "hours") | null;
    bitrate_kbps: number;
    resolution_width: number;
    resolution_height: number;
  } | null;
}) {
  return await apiClient.POST("/api/v1/observations/start", {
    body: request,
  });
}

/**
 * Get active observation for a specific camera.
 */
export async function getActiveObservationByCamera(cameraId: number) {
  return await apiClient.GET("/api/v1/observations/camera/{camera_id}/active", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Get observation by ID.
 */
export async function getObservation(observationId: number) {
  return await apiClient.GET("/api/v1/observations/{observation_id}", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Get observation status (progress, frame count, etc.).
 */
export async function getObservationStatus(observationId: number) {
  return await apiClient.GET("/api/v1/observations/{observation_id}/status", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Stop an observation.
 */
export async function stopObservation(
  observationId: number,
  assembleVideo: boolean = true
) {
  return await apiClient.POST("/api/v1/observations/{observation_id}/stop", {
    params: { path: { observation_id: observationId } },
    body: { assemble_video: assembleVideo },
  });
}

/**
 * Delete an observation.
 */
export async function deleteObservation(observationId: number) {
  return await apiClient.DELETE("/api/v1/observations/{observation_id}", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Update observation notes.
 */
export async function updateObservationNotes(
  observationId: number,
  notes: string
) {
  return await apiClient.PUT("/api/v1/observations/{observation_id}/notes", {
    params: { path: { observation_id: observationId } },
    body: { notes },
  });
}

/**
 * Get observation thumbnail.
 */
export async function getObservationThumbnail(observationId: number) {
  return await apiClient.GET("/api/v1/observations/{observation_id}/thumbnail", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Get observation preview video.
 */
export async function getObservationPreview(observationId: number) {
  return await apiClient.GET("/api/v1/observations/{observation_id}/preview", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Generate preview video for observation.
 */
export async function generateObservationPreview(observationId: number) {
  return await apiClient.POST(
    "/api/v1/observations/{observation_id}/generate-preview",
    {
      params: { path: { observation_id: observationId } },
    }
  );
}

/**
 * Get observation media files.
 */
export async function getObservationMedia(observationId: number) {
  return await apiClient.GET("/api/v1/observations/{observation_id}/media", {
    params: { path: { observation_id: observationId } },
  });
}

/**
 * Batch delete observations (uses query params per OpenAPI spec).
 */
export async function batchDeleteObservations(observationIds: number[]) {
  return await apiClient.POST("/api/v1/observations/batch-delete", {
    params: { query: { observation_ids: observationIds } },
  });
}

/**
 * List all active observations.
 */
export async function listActiveObservations(cameraId?: number) {
  return await apiClient.GET("/api/v1/observations/active", {
    params: { query: cameraId ? { camera_id: cameraId } : {} },
  });
}

/**
 * List completed observations with pagination.
 */
export async function listCompletedObservations(options?: {
  camera_id?: number;
  observation_type?: string;
  limit?: number;
  offset?: number;
}) {
  return await apiClient.GET("/api/v1/observations/completed", {
    params: { query: options || {} },
  });
}
