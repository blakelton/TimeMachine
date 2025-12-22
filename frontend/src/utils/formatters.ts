/**
 * Shared formatting utilities.
 *
 * Centralizes common formatting functions to reduce duplication.
 */

import { SECONDS_PER_MINUTE, SECONDS_PER_HOUR } from "../constants";

/**
 * Format a date string to locale string representation.
 *
 * @param dateStr - ISO date string or null
 * @returns Formatted date string or placeholder for null
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString();
}

/**
 * Format a date string to relative time (e.g., "2 hours ago").
 *
 * @param dateStr - ISO date string
 * @returns Relative time string
 */
export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);

  if (diffSeconds < SECONDS_PER_MINUTE) {
    return "just now";
  }

  const diffMinutes = Math.floor(diffSeconds / SECONDS_PER_MINUTE);
  if (diffMinutes < SECONDS_PER_MINUTE) {
    return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  }

  const diffHours = Math.floor(diffMinutes / SECONDS_PER_MINUTE);
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  }

  return formatDate(dateStr);
}

/**
 * Format seconds to MM:SS duration string.
 *
 * @param totalSeconds - Total seconds to format
 * @returns Duration string in MM:SS format
 */
export function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE);
  const seconds = totalSeconds % SECONDS_PER_MINUTE;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Format seconds to HH:MM:SS duration string.
 *
 * @param totalSeconds - Total seconds to format
 * @returns Duration string in HH:MM:SS format
 */
export function formatDurationLong(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / SECONDS_PER_HOUR);
  const minutes = Math.floor((totalSeconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
  const seconds = Math.floor(totalSeconds % SECONDS_PER_MINUTE);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Format file size in bytes to human-readable string.
 *
 * @param bytes - Size in bytes
 * @returns Human-readable size string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";

  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${units[i]}`;
}

/**
 * Extract API error message from various error types.
 *
 * @param error - The error object
 * @param fallback - Default message if extraction fails
 * @returns Error message string
 */
export function extractApiError(error: unknown, fallback = "An error occurred"): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "object" && error !== null) {
    const err = error as Record<string, unknown>;

    // Check common error response shapes
    if (typeof err.message === "string") {
      return err.message;
    }
    if (typeof err.detail === "string") {
      return err.detail;
    }
    if (err.error && typeof err.error === "object") {
      const innerError = err.error as Record<string, unknown>;
      if (typeof innerError.message === "string") {
        return innerError.message;
      }
    }
  }

  if (typeof error === "string") {
    return error;
  }

  return fallback;
}
