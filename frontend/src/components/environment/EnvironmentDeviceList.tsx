/**
 * List of environment devices with loading/error/empty states
 */

import { Button } from "../Button";
import { EnvironmentDeviceCard } from "./EnvironmentDeviceCard";
import type { components } from "../../types/api";

type EnvironmentDeviceResponse = components["schemas"]["EnvironmentDeviceResponse"];
type DeviceTypeInfo = components["schemas"]["DeviceTypeInfo"];

interface EnvironmentDeviceListProps {
  devices: EnvironmentDeviceResponse[];
  deviceTypes: DeviceTypeInfo[];
  isLoading: boolean;
  error: Error | null;
  onAddDevice: () => void;
  onToggleEnabled: (device: EnvironmentDeviceResponse) => void;
  onEditDevice: (device: EnvironmentDeviceResponse) => void;
  onDeleteDevice: (device: EnvironmentDeviceResponse) => void;
  isToggling?: boolean;
}

export function EnvironmentDeviceList({
  devices,
  deviceTypes,
  isLoading,
  error,
  onAddDevice,
  onToggleEnabled,
  onEditDevice,
  onDeleteDevice,
  isToggling = false,
}: EnvironmentDeviceListProps) {
  const getDeviceTypeInfo = (type: string): DeviceTypeInfo | undefined => {
    return deviceTypes.find((dt) => dt.type === type);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="panel-loading">
        <div className="loading-spinner"></div>
        <p>Loading devices...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="panel-error">
        <p>Failed to load devices. Please try again.</p>
      </div>
    );
  }

  // Empty state
  if (devices.length === 0) {
    return (
      <div className="panel-empty">
        <div className="empty-icon">🌡️</div>
        <h3>No feedback devices configured</h3>
        <p>Add sensors to monitor environmental conditions</p>
        <Button variant="primary" onClick={onAddDevice}>
          Add Device
        </Button>
      </div>
    );
  }

  // Devices list
  return (
    <div className="devices-list">
      {devices.map((device) => (
        <EnvironmentDeviceCard
          key={device.id}
          device={device}
          deviceTypeInfo={getDeviceTypeInfo(device.device_type)}
          onToggleEnabled={onToggleEnabled}
          onEdit={onEditDevice}
          onDelete={onDeleteDevice}
          isToggling={isToggling}
        />
      ))}
    </div>
  );
}
