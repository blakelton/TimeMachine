/**
 * Custom hook for API mutations with standardized error handling and toast notifications.
 *
 * This hook wraps TanStack Query's useMutation to provide:
 * - Automatic toast notifications on success/error
 * - Consistent error message extraction
 * - Simplified mutation configuration
 *
 * Reduces code duplication across 12+ components that follow the same
 * mutation pattern: call API -> show toast -> handle errors.
 *
 * @example
 * ```tsx
 * const updateMutation = useApiMutation(
 *   (data: UpdateData) => apiClient.PATCH('/api/endpoint', { body: data }),
 *   {
 *     successMessage: 'Updated successfully',
 *     errorMessage: 'Failed to update',
 *     onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data'] }),
 *   }
 * );
 *
 * // Use it
 * updateMutation.mutate(newData);
 * ```
 */

import { useMutation } from "@tanstack/react-query";
import type { UseMutationOptions, UseMutationResult } from "@tanstack/react-query";
import { useToast } from "../contexts/ToastContext";

/**
 * Options for configuring API mutations
 */
export interface ApiMutationOptions<TData> {
  /**
   * Success message to display in toast notification.
   * If not provided, no success toast is shown.
   */
  successMessage?: string;

  /**
   * Error message to display in toast notification.
   * Falls back to error.detail from API if available.
   */
  errorMessage?: string;

  /**
   * Callback invoked after successful mutation.
   * Typically used for cache invalidation or navigation.
   */
  onSuccess?: (data: TData) => void;

  /**
   * Callback invoked after failed mutation.
   * Allows custom error handling beyond toast notification.
   */
  onError?: (error: any) => void;
}

/**
 * Custom hook for API mutations with standardized error handling.
 *
 * @param mutationFn - Async function that performs the mutation
 * @param options - Configuration options for success/error handling
 * @returns TanStack Query mutation result
 */
export function useApiMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options?: ApiMutationOptions<TData>
): UseMutationResult<TData, any, TVariables, unknown> {
  const toast = useToast();

  const mutationOptions: UseMutationOptions<TData, any, TVariables> = {
    mutationFn,
    onSuccess: (data) => {
      // Show success toast if message provided
      if (options?.successMessage) {
        toast.success(options.successMessage);
      }

      // Invoke custom success callback
      options?.onSuccess?.(data);
    },
    onError: (error: any) => {
      // Extract error message with fallback chain:
      // 1. API error detail (from FastAPI error responses)
      // 2. Custom error message from options
      // 3. Generic fallback
      const message =
        error?.detail || options?.errorMessage || "Operation failed";

      toast.error(message);

      // Invoke custom error callback
      options?.onError?.(error);
    },
  };

  return useMutation(mutationOptions);
}
