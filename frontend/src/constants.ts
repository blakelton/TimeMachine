/**
 * Application-wide constants.
 *
 * This module centralizes magic numbers and configuration constants
 * to improve maintainability and reduce duplication.
 */

// =============================================================================
// TIMING CONSTANTS (milliseconds unless noted)
// =============================================================================

/** Default toast notification duration */
export const TOAST_DURATION_MS = 5000;

/** Camera status polling interval */
export const CAMERA_STATUS_POLL_INTERVAL_MS = 5000;

/** Observation status polling interval */
export const OBSERVATION_STATUS_POLL_INTERVAL_MS = 2000;

/** Camera list stale time for caching */
export const CAMERA_LIST_STALE_TIME_MS = 30000;

/** Preview reconnect delays */
export const PREVIEW_MAX_DELAY_MS = 2000;
export const PREVIEW_STREAM_READY_TIMEOUT_MS = 5000;


// =============================================================================
// VIDEO DEFAULTS
// =============================================================================

/** Default frames per second for recording/timelapse output */
export const DEFAULT_FPS = 30;
export const MAX_FPS = 60;

/** Default timelapse interval between captures (seconds) */
export const DEFAULT_TIMELAPSE_INTERVAL_SECONDS = 60;

/** Default recording duration (seconds) */
export const DEFAULT_RECORDING_DURATION_SECONDS = 30;


// =============================================================================
// STORAGE CONSTANTS
// =============================================================================

/** Default retention period in days */
export const DEFAULT_RETENTION_DAYS = 30;


// =============================================================================
// TIME FORMATTING
// =============================================================================

/** Seconds per minute */
export const SECONDS_PER_MINUTE = 60;

/** Seconds per hour */
export const SECONDS_PER_HOUR = 3600;


// =============================================================================
// UI CONSTANTS
// =============================================================================

/** Maximum disk size fallback when unknown (GB) */
export const DEFAULT_DISK_SIZE_GB = 100;
