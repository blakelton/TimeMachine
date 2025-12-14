# Feature: Frontend URL Fixes - Remove Hardcoded localhost

## Overview
Fix hardcoded `localhost:8000` URLs in frontend components that will break in production. These should use relative URLs so nginx can properly proxy requests to the backend.

## Problem

Several components have hardcoded the API URL as `http://localhost:8000` instead of using relative URLs. This works during local development but fails in production where:
- The frontend is served from `http://timemachine.local`
- API calls should go through nginx at `/api/*`
- Direct calls to `localhost:8000` would try to reach the user's local machine

## Affected Files

### 1. PreviewTab.tsx (Line 57-60)

**Current (broken in production):**
```typescript
const getStreamUrl = () => {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  return `${baseUrl}/api/v1/cameras/${cameraId}/preview/stream`;
};
```

**Fixed:**
```typescript
const getStreamUrl = () => {
  return `/api/v1/cameras/${cameraId}/preview/stream`;
};
```

### 2. CaptureTab.tsx (Line 51-52)

**Current (broken in production):**
```typescript
const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const imageUrl = `${baseUrl}${(data as any).file_url}`;
```

**Fixed:**
```typescript
// file_url is already an absolute path like "/media/stills/capture.jpg"
const imageUrl = (data as any).file_url;
```

### 3. client.ts - Already Fixed

The main API client was already fixed to use relative URLs:
```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "";
```

## Implementation

### Task 1: Fix PreviewTab.tsx

File: `frontend/src/components/camera/PreviewTab.tsx`

```diff
- const getStreamUrl = () => {
-   const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
-   return `${baseUrl}/api/v1/cameras/${cameraId}/preview/stream`;
- };
+ const getStreamUrl = () => {
+   // Use relative URL - nginx will proxy to backend
+   return `/api/v1/cameras/${cameraId}/preview/stream`;
+ };
```

### Task 2: Fix CaptureTab.tsx

File: `frontend/src/components/camera/CaptureTab.tsx`

```diff
  if (data) {
-   // Set the captured image URL
-   const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
-   const imageUrl = `${baseUrl}${(data as any).file_url}`;
+   // file_url is already an absolute path served by nginx
+   const imageUrl = (data as any).file_url;
    setLastCaptureUrl(imageUrl);
```

### Task 3: Verify No Other Hardcoded URLs

Search for any other instances:
```bash
grep -r "localhost:8000" frontend/src/
grep -r "VITE_API_URL" frontend/src/
```

Expected results after fixes:
- `client.ts` - Uses `VITE_API_URL` with empty string fallback ✓
- No other files should reference `localhost:8000`

## Testing Checklist

### Local Development
- [ ] Preview stream works at `http://localhost:5173` (Vite dev server)
- [ ] Capture works and displays image
- [ ] All API calls work through Vite proxy (if configured) or direct

### Production (on Pi)
- [ ] Preview stream works at `http://timemachine.local`
- [ ] Capture works and displays image
- [ ] All API calls go through nginx `/api/*`
- [ ] Media files load from `/media/*`

## Additional Recommendations

### 1. Add Vite Proxy for Development

To make local development work without hardcoded URLs, add proxy config to `vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

This allows the frontend dev server to proxy API requests to the backend, matching production behavior.

### 2. Environment Variable Documentation

Update `.env.example`:
```bash
# API Configuration
# For local development with Vite proxy, leave empty
# For direct backend access, set to http://localhost:8000
VITE_API_URL=

# WebSocket Configuration
# For local development with Vite proxy, leave empty
# For direct backend access, set to ws://localhost:8000
VITE_WS_URL=
```

## Estimated Effort

**Trivial** - 2 line changes across 2 files, plus testing.

## Priority

**High** - These bugs prevent the application from working in production. The camera save bug was just fixed (same root cause), but preview and capture are still broken.

---

**Status**: `.ready.md` - Ready for implementation
