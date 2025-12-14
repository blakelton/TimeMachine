/**
 * WebSocket message protocol types matching backend
 */

/**
 * System statistics update message
 */
export interface WSStatsUpdate {
  type: "stats_update";
  cpu_percent: number;
  memory_percent: number;
  disk_free_gb: number;
  temperature_celsius: number | null;
  timestamp: string;
}

/**
 * Camera event message
 */
export interface WSCameraEvent {
  type: "camera_event";
  camera_id: number;
  event: "online" | "offline" | "recording_started" | "recording_stopped" | "error";
  message?: string | null;
  timestamp: string;
}

/**
 * Job update message
 */
export interface WSJobUpdate {
  type: "job_update";
  job_id: number;
  camera_id: number;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  progress?: number | null; // 0-100
  timestamp: string;
}

/**
 * Error message
 */
export interface WSError {
  type: "error";
  code: string;
  message: string;
  timestamp: string;
}

/**
 * Union type of all possible WebSocket messages
 */
export type WSMessage = WSStatsUpdate | WSCameraEvent | WSJobUpdate | WSError;

/**
 * Type guards for message discrimination
 */
export function isStatsUpdate(msg: WSMessage): msg is WSStatsUpdate {
  return msg.type === "stats_update";
}

export function isCameraEvent(msg: WSMessage): msg is WSCameraEvent {
  return msg.type === "camera_event";
}

export function isJobUpdate(msg: WSMessage): msg is WSJobUpdate {
  return msg.type === "job_update";
}

export function isError(msg: WSMessage): msg is WSError {
  return msg.type === "error";
}

/**
 * WebSocket message handler type
 */
export type MessageHandler<T extends WSMessage = WSMessage> = (message: T) => void;

/**
 * WebSocket connection state
 */
export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";
