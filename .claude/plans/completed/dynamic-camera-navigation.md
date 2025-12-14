# Feature: Dynamic Camera Navigation Tabs

## Overview
Add dynamic camera tabs to the main navigation that appear when cameras are configured in the system. Each camera gets its own navigation tab that links to the camera's observation page (preview, capture, record, timelapse).

## Current State

**Layout.tsx** - Static navigation with only "Home" and "System" links:
```tsx
<nav className="main-nav">
  <Link to="/" className={...}>Home</Link>
  <Link to="/system" className={...}>System</Link>
</nav>
```

**Routing** - Already configured in App.tsx:
- `/camera/:cameraId/:tab?` - CameraPage with nested tabs (preview, capture, record, timelapse)

**CameraPage** - Already exists with full functionality:
- Preview tab (live MJPEG stream)
- Capture tab (still images)
- Record tab (video recording)
- Timelapse tab (timelapse capture)

## Requirements

### Functional Requirements
- FR1: Display a navigation tab for each configured camera
- FR2: Show only enabled cameras in navigation (optional: show disabled cameras grayed out)
- FR3: Camera tabs appear between "Home" and "System" links
- FR4: Clicking camera tab navigates to `/camera/:cameraId/preview`
- FR5: Active camera tab highlighted when on that camera's page
- FR6: Navigation updates automatically when cameras are added/removed
- FR7: Visual separator between static nav and camera tabs for clarity

### Non-Functional Requirements
- NFR1: Camera list cached and refreshed on window focus
- NFR2: No layout shift when cameras load (reserve space or use loading indicator)
- NFR3: Mobile-responsive: camera tabs in hamburger menu on small screens
- NFR4: Accessible: proper ARIA labels for dynamic navigation

## Implementation Plan

### Changes to Layout.tsx

1. **Add TanStack Query for cameras list**
   ```tsx
   import { useQuery } from "@tanstack/react-query";
   import { apiClient } from "../api/client";

   const { data: camerasData } = useQuery({
     queryKey: ["cameras"],
     queryFn: async () => {
       const response = await apiClient.GET("/api/v1/cameras");
       if (response.error) throw new Error("Failed to fetch cameras");
       return response.data;
     },
     staleTime: 30000, // Cache for 30 seconds
     refetchOnWindowFocus: true,
   });

   const cameras = camerasData?.cameras || [];
   ```

2. **Update isActive helper to handle camera routes**
   ```tsx
   const isActive = (path: string) => location.pathname === path;
   const isCameraActive = (cameraId: number) =>
     location.pathname.startsWith(`/camera/${cameraId}`);
   ```

3. **Render dynamic camera tabs**
   ```tsx
   <nav className="main-nav">
     <Link to="/" className={isActive("/") ? "nav-link active" : "nav-link"}>
       Home
     </Link>

     {/* Dynamic camera tabs */}
     {cameras.length > 0 && (
       <>
         <span className="nav-separator" aria-hidden="true">|</span>
         {cameras
           .filter(cam => cam.enabled)
           .map(camera => (
             <Link
               key={camera.id}
               to={`/camera/${camera.id}/preview`}
               className={isCameraActive(camera.id) ? "nav-link active" : "nav-link"}
               title={`${camera.name} (${camera.camera_type.toUpperCase()})`}
             >
               {camera.name}
             </Link>
           ))}
       </>
     )}

     <span className="nav-separator" aria-hidden="true">|</span>
     <Link to="/system" className={...}>System</Link>
   </nav>
   ```

### Changes to Layout.css

1. **Add separator styling**
   ```css
   .nav-separator {
     color: rgba(255, 255, 255, 0.3);
     margin: 0 0.5rem;
     user-select: none;
   }
   ```

2. **Add camera tab specific styles (optional)**
   ```css
   .nav-link.camera-tab {
     /* Slightly different style to distinguish camera tabs */
     font-size: 0.95rem;
   }
   ```

3. **Mobile handling - wrap camera tabs**
   ```css
   @media (max-width: 768px) {
     .main-nav {
       flex-wrap: wrap;
       gap: 0.5rem;
     }

     .nav-separator {
       display: none;
     }
   }
   ```

## Visual Design

### Desktop (>768px)
```
┌────────────────────────────────────────────────────────────────────┐
│ TimeMachine    Home | Camera 1 | Camera 2 | System        [Logout] │
└────────────────────────────────────────────────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────────┐
│ TimeMachine          │
├──────────────────────┤
│ Home   Camera 1      │
│ Camera 2   System    │
├──────────────────────┤
│ [Logout]             │
└──────────────────────┘
```

## Edge Cases

1. **No cameras configured**: Only show Home and System links (current behavior)
2. **All cameras disabled**: Show no camera tabs (or show grayed out - TBD)
3. **Many cameras (5+)**: Consider overflow handling or dropdown menu
4. **Long camera names**: Truncate with ellipsis, show full name on hover (title attribute)
5. **Camera deleted while on its page**: Show 404 or redirect to Home

## Testing Checklist

- [ ] Camera tabs appear after adding first camera
- [ ] Clicking camera tab navigates to correct camera page
- [ ] Active tab highlighted when on camera page
- [ ] Tab still active on camera sub-routes (/camera/1/record, etc.)
- [ ] Camera tabs update when camera is added
- [ ] Camera tabs update when camera is deleted
- [ ] Camera tabs update when camera is disabled/enabled
- [ ] Mobile layout works correctly
- [ ] No layout shift during initial load
- [ ] Keyboard navigation works for all nav links

## Files to Modify

1. `frontend/src/components/Layout.tsx` - Add camera query and dynamic tabs
2. `frontend/src/components/Layout.css` - Add separator and mobile styles

## Estimated Effort

**Small** - This is a focused change:
- ~30 lines of new TypeScript code
- ~15 lines of new CSS
- Uses existing query patterns from CamerasPanel
- Routing already configured

## Questions for Review

1. **Disabled cameras**: Should disabled cameras appear grayed out in nav, or be completely hidden?
2. **Camera limit**: If user has many cameras (5+), should we use a dropdown/overflow menu?
3. **Tab naming**: Use camera name directly, or abbreviate? (e.g., "Cam 1" vs "USB Camera 1")
4. **Loading state**: Show skeleton tabs while cameras load, or just render when ready?

---

**Status**: `.ready.md` - Ready for implementation after review
