/**
 * TanStack Query configuration
 */

import { QueryClient } from "@tanstack/react-query";

/**
 * Global QueryClient instance with default configuration
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000, // Data considered fresh for 5 seconds
      gcTime: 10 * 60 * 1000, // Cache for 10 minutes (was cacheTime)
      retry: 1, // Retry failed requests once
      refetchOnWindowFocus: false, // Don't refetch on window focus by default
    },
    mutations: {
      retry: false, // Don't retry mutations
    },
  },
});
