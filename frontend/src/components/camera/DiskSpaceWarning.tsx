/**
 * Disk space warning component
 * Shows warning banner when disk space is low
 */

import type { ReactNode } from "react";
import "./DiskSpaceWarning.css";

export interface DiskSpaceWarningProps {
  diskFreeGB: number;
  diskTotalGB?: number;
  warningThresholdPercent?: number;
  criticalThresholdPercent?: number;
  className?: string;
}

export function DiskSpaceWarning({
  diskFreeGB,
  diskTotalGB,
  warningThresholdPercent = 10,
  criticalThresholdPercent = 5,
  className = "",
}: DiskSpaceWarningProps) {
  // Calculate percentage if total is provided
  let freePercent: number | null = null;
  if (diskTotalGB && diskTotalGB > 0) {
    freePercent = (diskFreeGB / diskTotalGB) * 100;
  }

  // Determine warning level
  let level: "none" | "warning" | "critical" = "none";
  if (freePercent !== null) {
    if (freePercent <= criticalThresholdPercent) {
      level = "critical";
    } else if (freePercent <= warningThresholdPercent) {
      level = "warning";
    }
  }

  // Don't render if no warning
  if (level === "none") {
    return null;
  }

  // Prepare message
  let message: ReactNode;
  if (level === "critical") {
    message = (
      <>
        <strong>Critical:</strong> Only {diskFreeGB.toFixed(1)} GB disk space
        remaining. Recording and timelapse operations may fail.
      </>
    );
  } else {
    message = (
      <>
        <strong>Warning:</strong> Low disk space ({diskFreeGB.toFixed(1)} GB
        remaining). Consider freeing up space.
      </>
    );
  }

  return (
    <div
      className={`disk-space-warning disk-space-warning--${level} ${className}`}
      role="alert"
    >
      <div className="disk-space-warning__icon">
        {level === "critical" ? "⚠️" : "ℹ️"}
      </div>
      <div className="disk-space-warning__message">{message}</div>
    </div>
  );
}
