/**
 * WebSocket message protocol types for real-time updates
 */

/**
 * System statistics message
 */
export interface StatsMessage {
  type: "stats";
  data: {
    cpu_percent: number;
    memory_percent: number;
    memory_available_mb: number;
    memory_total_mb: number;
    memory_status: "ok" | "warning" | "critical";
    disk_percent: number;
    disk_available_mb: number;
    disk_total_mb: number;
    cpu_temp_c: number | null;
    throttled: {
      under_voltage: boolean;
      frequency_capped: boolean;
      currently_throttled: boolean;
      soft_temp_limit: boolean;
    };
  };
  timestamp: string;
}

/**
 * Camera status update message
 */
export interface CameraStatusMessage {
  type: "camera_status";
  data: {
    camera_id: number;
    status: "online" | "offline" | "busy" | "error";
    active_operation: "idle" | "preview" | "recording" | "timelapse" | "capture";
  };
  timestamp: string;
}

/**
 * System event message
 */
export interface EventMessage {
  type: "event";
  data: {
    event_type: string;
    severity: "info" | "warning" | "error";
    message: string;
    details?: Record<string, unknown>;
  };
  timestamp: string;
}

/**
 * Job status update message
 */
export interface JobStatusMessage {
  type: "job_status";
  data: {
    job_id: number;
    camera_id: number;
    status: "pending" | "running" | "completed" | "failed" | "interrupted";
    progress?: number; // For timelapse
  };
  timestamp: string;
}

/**
 * Union type of all possible WebSocket messages
 */
export type WebSocketMessage =
  | StatsMessage
  | CameraStatusMessage
  | EventMessage
  | JobStatusMessage;

/**
 * WebSocket message handler type
 */
export type MessageHandler<T extends WebSocketMessage = WebSocketMessage> = (
  message: T
) => void;

/**
 * WebSocket connection state
 */
export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";
