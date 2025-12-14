/**
 * Dialog for confirming timelapse cleanup
 */

import { Modal } from "../Modal";
import { Button } from "../Button";
import "./TimelapseCleanupDialog.css";

interface TimelapseCleanupDialogProps {
  isOpen: boolean;
  frameCount: number;
  diskUsage: string;
  onFinalize: () => void;
  onDelete: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function TimelapseCleanupDialog({
  isOpen,
  frameCount,
  diskUsage,
  onFinalize,
  onDelete,
  onCancel,
  loading = false,
}: TimelapseCleanupDialogProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title="Cleanup Interrupted Timelapse"
      width="md"
    >
      <div className="timelapse-cleanup-dialog">
        <div className="timelapse-cleanup-dialog__info">
          <p>
            You have <strong>{frameCount} frames</strong> from an interrupted
            timelapse using <strong>{diskUsage}</strong> of disk space.
          </p>
          <p>What would you like to do?</p>
        </div>

        <div className="timelapse-cleanup-dialog__options">
          <div className="timelapse-cleanup-dialog__option">
            <h4>Create Video</h4>
            <p>Generate a timelapse video from the captured frames.</p>
            <Button
              variant="primary"
              onClick={onFinalize}
              disabled={loading}
              className="timelapse-cleanup-dialog__button"
            >
              {loading ? "Processing..." : "Create Video from Frames"}
            </Button>
          </div>

          <div className="timelapse-cleanup-dialog__divider">or</div>

          <div className="timelapse-cleanup-dialog__option timelapse-cleanup-dialog__option--danger">
            <h4>Delete Frames</h4>
            <p>
              Permanently delete all captured frames. This cannot be undone.
            </p>
            <Button
              variant="danger"
              onClick={onDelete}
              disabled={loading}
              className="timelapse-cleanup-dialog__button"
            >
              {loading ? "Deleting..." : "Delete All Frames"}
            </Button>
          </div>
        </div>

        <div className="timelapse-cleanup-dialog__actions">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
