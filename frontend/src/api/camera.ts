/**
 * Typed API wrappers for camera endpoints.
 *
 * These wrappers provide proper TypeScript types and eliminate the need for
 * `as any` casts when calling path-parameterized endpoints.
 */

import { apiClient } from "./client";

/**
 * Capture a still image from a camera.
 */
export async function captureImage(cameraId: number, filename?: string | null) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/capture", {
    params: {
      path: { camera_id: cameraId },
      query: filename ? { filename } : undefined,
    },
  });
}

/**
 * Start camera preview.
 */
export async function startPreview(cameraId: number, fps?: number) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/preview/start", {
    params: {
      path: { camera_id: cameraId },
      query: fps ? { fps } : undefined,
    },
  });
}

/**
 * Stop camera preview.
 */
export async function stopPreview(cameraId: number) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/preview/stop", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Get preview status.
 */
export async function getPreviewStatus(cameraId: number) {
  return await apiClient.GET("/api/v1/cameras/{camera_id}/preview/status", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Start recording.
 */
export async function startRecording(
  cameraId: number,
  durationSeconds?: number | null,
  filename?: string | null
) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/recording/start", {
    params: { path: { camera_id: cameraId } },
    body: {
      duration_seconds: durationSeconds,
      filename,
    },
  });
}

/**
 * Stop recording.
 */
export async function stopRecording(cameraId: number) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/recording/stop", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Get recording status.
 */
export async function getRecordingStatus(cameraId: number) {
  return await apiClient.GET("/api/v1/cameras/{camera_id}/recording/status", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Start timelapse.
 */
export async function startTimelapse(
  cameraId: number,
  config: {
    interval_seconds: number;
    total_frames?: number | null;
    duration_hours?: number | null;
    quality: number;
    resolution_width: number;
    resolution_height: number;
    output_fps: number;
  }
) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/timelapse/start", {
    params: { path: { camera_id: cameraId } },
    body: { config },
  });
}

/**
 * Stop timelapse.
 */
export async function stopTimelapse(
  cameraId: number,
  assembleVideo: boolean = true
) {
  return await apiClient.POST("/api/v1/cameras/{camera_id}/timelapse/stop", {
    params: { path: { camera_id: cameraId } },
    body: { assemble_video: assembleVideo },
  });
}

/**
 * Get timelapse status.
 */
export async function getTimelapseStatus(cameraId: number) {
  return await apiClient.GET("/api/v1/cameras/{camera_id}/timelapse/status", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Check camera health.
 */
export async function checkCameraHealth(cameraId: number) {
  return await apiClient.GET("/api/v1/cameras/{camera_id}/health", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Get single camera by ID.
 */
export async function getCamera(cameraId: number) {
  return await apiClient.GET("/api/v1/cameras/{camera_id}", {
    params: { path: { camera_id: cameraId } },
  });
}

/**
 * Update camera settings.
 */
export async function updateCamera(
  cameraId: number,
  updates: {
    name?: string | null;
    device_path?: string | null;
    camera_type?: string | null;
    enabled?: boolean | null;
    hardware_id?: string | null;
    capabilities?: Record<string, unknown> | null;
    default_settings?: Record<string, unknown> | null;
    notes?: string | null;
  }
) {
  return await apiClient.PATCH("/api/v1/cameras/{camera_id}", {
    params: { path: { camera_id: cameraId } },
    body: updates,
  });
}

/**
 * Delete camera.
 */
export async function deleteCamera(cameraId: number) {
  return await apiClient.DELETE("/api/v1/cameras/{camera_id}", {
    params: { path: { camera_id: cameraId } },
  });
}
