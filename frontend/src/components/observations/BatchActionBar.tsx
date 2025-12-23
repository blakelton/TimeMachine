/**
 * Batch action bar for managing multiple selected observations.
 */

import { useState } from "react";
import { ConfirmDialog } from "../ConfirmDialog";
import { getMediaUrl } from "../../hooks/useObservations";
import "./BatchActionBar.css";

interface BatchActionBarProps {
  selectedCount: number;
  totalCount: number;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onDelete: () => void;
  onDownload: () => void;
  isDeleting?: boolean;
  isDownloading?: boolean;
  selectedIds: Set<number>;
}

export function BatchActionBar({
  selectedCount,
  totalCount,
  onSelectAll,
  onDeselectAll,
  onDelete,
  onDownload,
  isDeleting = false,
  isDownloading = false,
}: BatchActionBarProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDelete = () => {
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    await onDelete();
    setShowDeleteConfirm(false);
  };

  const allSelected = selectedCount === totalCount && totalCount > 0;

  return (
    <>
      <div className="batch-action-bar">
        <div className="batch-action-bar__selection">
          <button
            className="batch-action-bar__toggle"
            onClick={allSelected ? onDeselectAll : onSelectAll}
          >
            {allSelected ? "Deselect All" : "Select All"}
          </button>
          <span className="batch-action-bar__count">
            {selectedCount} of {totalCount} selected
          </span>
        </div>

        <div className="batch-action-bar__actions">
          <button
            className="batch-action-bar__btn batch-action-bar__btn--download"
            onClick={onDownload}
            disabled={selectedCount === 0 || isDownloading}
          >
            {isDownloading ? "Downloading..." : `Download (${selectedCount})`}
          </button>
          <button
            className="batch-action-bar__btn batch-action-bar__btn--delete"
            onClick={handleDelete}
            disabled={selectedCount === 0 || isDeleting}
          >
            {isDeleting ? "Deleting..." : `Delete (${selectedCount})`}
          </button>
          <button
            className="batch-action-bar__btn batch-action-bar__btn--cancel"
            onClick={onDeselectAll}
          >
            Cancel
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        title="Delete Observations"
        message={`Are you sure you want to delete ${selectedCount} observation${selectedCount !== 1 ? "s" : ""}? This action cannot be undone.`}
        confirmText="Delete All"
        cancelText="Cancel"
        variant="danger"
        loading={isDeleting}
      />
    </>
  );
}

/**
 * Download multiple files sequentially
 */
export async function downloadMultipleFiles(observationIds: number[]): Promise<void> {
  for (const id of observationIds) {
    const url = getMediaUrl(id);
    const link = document.createElement("a");
    link.href = url;
    link.download = `observation_${id}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    // Small delay between downloads to avoid browser blocking
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
}
