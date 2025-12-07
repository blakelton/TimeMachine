/**
 * Confirmation dialog component
 */

import { Modal } from "./Modal";
import { Button } from "./Button";
import "./ConfirmDialog.css";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "default" | "danger";
  loading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  loading = false,
}: ConfirmDialogProps) {
  const handleConfirm = async () => {
    await onConfirm();
    if (!loading) {
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      width="sm"
      closeOnBackdrop={!loading}
      closeOnEscape={!loading}
      showCloseButton={!loading}
    >
      <div className="confirm-dialog">
        <div className={`confirm-message ${variant === "danger" ? "confirm-danger" : ""}`}>
          {variant === "danger" && (
            <div className="confirm-icon" aria-hidden="true">
              ⚠
            </div>
          )}
          <p>{message}</p>
        </div>

        <div className="confirm-actions">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            variant={variant === "danger" ? "danger" : "primary"}
            onClick={handleConfirm}
            loading={loading}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
