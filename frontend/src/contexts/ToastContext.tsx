/**
 * Toast notification context and provider
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from "react";
import type { ReactNode } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (type: ToastType, message: string, duration?: number) => void;
  removeToast: (id: string) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  /**
   * Timer management to prevent memory leaks.
   * Stores all active toast timers keyed by toast ID.
   */
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    // Clear the timer if it exists
    const timerId = timers.current.get(id);
    if (timerId) {
      clearTimeout(timerId);
      timers.current.delete(id);
    }

    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string, duration: number = 5000) => {
      const id = `toast-${Date.now()}-${Math.random()}`;
      const newToast: Toast = { id, type, message, duration };

      setToasts((prev) => [...prev, newToast]);

      // Auto-dismiss after duration
      if (duration > 0) {
        const timerId = setTimeout(() => {
          removeToast(id);
        }, duration);

        // Store timer for cleanup
        timers.current.set(id, timerId);
      }
    },
    [removeToast]
  );

  /**
   * Cleanup effect: Clear all active timers on unmount to prevent memory leaks.
   */
  useEffect(() => {
    return () => {
      timers.current.forEach((timer) => clearTimeout(timer));
      timers.current.clear();
    };
  }, []);

  // Convenience methods for different toast types
  const success = useCallback(
    (message: string, duration?: number) => addToast("success", message, duration),
    [addToast]
  );

  const error = useCallback(
    (message: string, duration?: number) => addToast("error", message, duration),
    [addToast]
  );

  const warning = useCallback(
    (message: string, duration?: number) => addToast("warning", message, duration),
    [addToast]
  );

  const info = useCallback(
    (message: string, duration?: number) => addToast("info", message, duration),
    [addToast]
  );

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
