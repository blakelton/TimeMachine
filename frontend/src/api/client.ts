/**
 * API client using openapi-fetch with full type safety from generated OpenAPI types.
 */

import createClient from "openapi-fetch";
import type { paths } from "../types/api";

// Base URL for the API
// In production, use empty string to make requests relative to the current origin
// (nginx will proxy /api/* to the backend)
// In development, VITE_API_URL can be set to http://localhost:8000
const BASE_URL = import.meta.env.VITE_API_URL || "";

/**
 * Typed API client
 *
 * Usage:
 * ```ts
 * const { data, error } = await apiClient.GET("/api/v1/cameras");
 * if (data) {
 *   // data is typed as CameraListResponse
 * }
 * ```
 */
export const apiClient = createClient<paths>({ baseUrl: BASE_URL });

/**
 * Authorization header storage for optional HTTP Basic Auth
 */
let authHeader: string | null = null;

/**
 * Set authorization header for all requests
 */
export function setAuthHeader(username: string, password: string) {
  const credentials = btoa(`${username}:${password}`);
  authHeader = `Basic ${credentials}`;
  apiClient.use({
    onRequest({ request }) {
      if (authHeader) {
        request.headers.set("Authorization", authHeader);
      }
    },
  });
}

/**
 * Clear authorization header
 */
export function clearAuthHeader() {
  authHeader = null;
}

/**
 * Check if auth is configured
 */
export function hasAuth(): boolean {
  return authHeader !== null;
}
