/**
 * Grid layout component for displaying observation tiles.
 */

import { memo } from "react";
import { ObservationTile } from "./ObservationTile";
import type { CompletedObservation } from "../../hooks/useObservations";
import "./ObservationGrid.css";

interface ObservationGridProps {
  observations: CompletedObservation[];
  onSelect: (observation: CompletedObservation, index: number) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  selectionMode?: boolean;
  selectedIds?: Set<number>;
  onToggleSelect?: (id: number) => void;
}

export const ObservationGrid = memo(function ObservationGrid({
  observations,
  onSelect,
  isLoading,
  emptyMessage = "No observations found",
  selectionMode = false,
  selectedIds = new Set(),
  onToggleSelect,
}: ObservationGridProps) {
  if (isLoading) {
    return (
      <div className="observation-grid observation-grid--loading">
        {/* Skeleton tiles */}
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="observation-tile-skeleton">
            <div className="skeleton-thumbnail" />
            <div className="skeleton-info">
              <div className="skeleton-line skeleton-line--title" />
              <div className="skeleton-line skeleton-line--subtitle" />
              <div className="skeleton-line skeleton-line--meta" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (observations.length === 0) {
    return (
      <div className="observation-grid__empty">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="observation-grid">
      {observations.map((observation, index) => (
        <ObservationTile
          key={observation.id}
          observation={observation}
          onClick={() => onSelect(observation, index)}
          selectionMode={selectionMode}
          isSelected={selectedIds.has(observation.id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  );
});
