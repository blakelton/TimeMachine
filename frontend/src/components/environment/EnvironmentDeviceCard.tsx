/**
 * Individual environment device card display
 */

import { Button } from "../Button";
import type { components } from "../../types/api";

type EnvironmentDeviceResponse = components["schemas"]["EnvironmentDeviceResponse"];
type DeviceTypeInfo = components["schemas"]["DeviceTypeInfo"];

interface EnvironmentDeviceCardProps {
  device: EnvironmentDeviceResponse;
  deviceTypeInfo?: DeviceTypeInfo;
  onToggleEnabled: (device: EnvironmentDeviceResponse) => void;
  onEdit: (device: EnvironmentDeviceResponse) => void;
  onDelete: (device: EnvironmentDeviceResponse) => void;
  isToggling?: boolean;
}

export function EnvironmentDeviceCard({
  device,
  deviceTypeInfo,
  onToggleEnabled,
  onEdit,
  onDelete,
  isToggling = false,
}: EnvironmentDeviceCardProps) {
  return (
    <div className="device-card">
      <div className="device-info">
        <div className="device-header">
          <h3>{device.name}</h3>
          <span className={`device-status ${device.enabled ? "enabled" : "disabled"}`}>
            {device.enabled ? "Enabled" : "Disabled"}
          </span>
        </div>
        <div className="device-details">
          <div className="device-detail">
            <span className="detail-label">Type:</span>
            <span className="detail-value">{deviceTypeInfo?.name || device.device_type}</span>
          </div>
          <div className="device-detail">
            <span className="detail-label">{deviceTypeInfo?.pin_label || "Pin"}:</span>
            <span className="detail-value">{device.pin_or_address}</span>
          </div>
          <div className="device-detail">
            <span className="detail-label">Poll:</span>
            <span className="detail-value">{device.poll_interval_seconds}s</span>
          </div>
          <div className="device-detail">
            <span className="detail-label">Temp:</span>
            <span className="detail-value">{device.temperature_unit === "F" ? "°F" : "°C"}</span>
          </div>
        </div>
        {device.notes && (
          <div className="device-notes">{device.notes}</div>
        )}
      </div>

      <div className="device-actions">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onToggleEnabled(device)}
          disabled={isToggling}
        >
          {device.enabled ? "Disable" : "Enable"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onEdit(device)}
        >
          Edit
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={() => onDelete(device)}
        >
          Delete
        </Button>
      </div>
    </div>
  );
}
