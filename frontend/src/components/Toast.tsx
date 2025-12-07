/**
 * Toast notification component
 */

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { useToast, type Toast as ToastType } from "../contexts/ToastContext";
import "./Toast.css";

interface ToastProps {
  toast: ToastType;
}

function ToastItem({ toast }: ToastProps) {
  const { removeToast } = useToast();

  useEffect(() => {
    // Set up auto-dismiss if duration is specified
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        removeToast(toast.id);
      }, toast.duration);

      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, removeToast]);

  const getToastIcon = () => {
    switch (toast.type) {
      case "success":
        return "✓";
      case "error":
        return "✕";
      case "warning":
        return "⚠";
      case "info":
        return "ℹ";
      default:
        return "ℹ";
    }
  };

  const handleClose = () => {
    removeToast(toast.id);
  };

  return (
    <div
      className={`toast toast-${toast.type}`}
      role="alert"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="toast-icon">{getToastIcon()}</div>
      <div className="toast-message">{toast.message}</div>
      <button
        className="toast-close"
        onClick={handleClose}
        aria-label="Close notification"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts } = useToast();

  // Render toasts in a portal to ensure they appear on top of everything
  return createPortal(
    <div className="toast-container" aria-label="Notifications">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>,
    document.body
  );
}
