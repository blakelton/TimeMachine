# Feature: MediaBrowser - Frontend Media Management

## Overview
Implement a MediaBrowser component that allows users to browse, preview, download, and delete their recorded media (recordings, stills, timelapses). This component will be integrated into the Camera Tabs UI.

## Dependencies
- **Requires**: Files API backend (see `files-api-backend.ready.md`)

## Current State
- RecordTab shows only current recording status, no history
- CaptureTab shows only last captured image
- TimelapseTab shows only current timelapse status
- No way to browse/manage media files

## Requirements

### Functional Requirements
- FR1: Display list of files (recordings, stills, or timelapses)
- FR2: Filter by camera when viewing from camera page
- FR3: Show file metadata (name, size, date, duration)
- FR4: Preview images in lightbox
- FR5: Play videos in modal player
- FR6: Download files
- FR7: Delete files with confirmation
- FR8: Pagination (load more)
- FR9: Sort by date, size, name

### Non-Functional Requirements
- NFR1: Lazy load thumbnails
- NFR2: Responsive grid layout
- NFR3: Keyboard navigation for modal
- NFR4: Loading states for all async operations

## Component Design

### MediaBrowser Component

```tsx
interface MediaBrowserProps {
  mediaType: "recordings" | "stills" | "timelapses";
  cameraId?: number;  // Optional: filter by camera
  limit?: number;     // Items per page (default: 12)
}
```

### File Structure

```
frontend/src/components/media/
├── MediaBrowser.tsx
├── MediaBrowser.css
├── MediaCard.tsx
├── MediaCard.css
├── VideoPlayer.tsx
├── VideoPlayer.css
├── ImageLightbox.tsx
├── ImageLightbox.css
└── index.ts
```

## Implementation Plan

### Phase 1: Core Components

**Task 1.1: Create MediaCard component**

File: `frontend/src/components/media/MediaCard.tsx`

```tsx
/**
 * Card component for displaying a single media file
 */

import { useState } from "react";
import { Button } from "../Button";
import "./MediaCard.css";

export interface MediaFile {
  filename: string;
  path: string;
  size_bytes: number;
  size_human: string;
  camera_id: number | null;
  camera_name: string | null;
  created_at: string;
  duration_seconds?: number;
  frame_count?: number;
  width?: number;
  height?: number;
}

interface MediaCardProps {
  file: MediaFile;
  mediaType: "recordings" | "stills" | "timelapses";
  onPreview: (file: MediaFile) => void;
  onDelete: (file: MediaFile) => void;
}

export function MediaCard({ file, mediaType, onPreview, onDelete }: MediaCardProps) {
  const [imageError, setImageError] = useState(false);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getThumbnailUrl = () => {
    if (mediaType === "stills") {
      return file.path;
    }
    // For videos, we'd need a thumbnail endpoint or use a placeholder
    return null;
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = file.path;
    link.download = file.filename;
    link.click();
  };

  return (
    <div className="media-card">
      <div className="media-card__preview" onClick={() => onPreview(file)}>
        {mediaType === "stills" && !imageError ? (
          <img
            src={getThumbnailUrl() || ""}
            alt={file.filename}
            className="media-card__image"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="media-card__placeholder">
            {mediaType === "recordings" && "🎬"}
            {mediaType === "timelapses" && "⏱️"}
            {mediaType === "stills" && "📷"}
          </div>
        )}
        {(mediaType === "recordings" || mediaType === "timelapses") && (
          <div className="media-card__play-overlay">▶</div>
        )}
      </div>

      <div className="media-card__info">
        <div className="media-card__filename" title={file.filename}>
          {file.filename}
        </div>
        <div className="media-card__meta">
          <span>{file.size_human}</span>
          {file.duration_seconds && (
            <span>{formatDuration(file.duration_seconds)}</span>
          )}
          {file.frame_count && <span>{file.frame_count} frames</span>}
        </div>
        <div className="media-card__date">{formatDate(file.created_at)}</div>
        {file.camera_name && (
          <div className="media-card__camera">{file.camera_name}</div>
        )}
      </div>

      <div className="media-card__actions">
        <Button size="sm" variant="outline" onClick={handleDownload}>
          Download
        </Button>
        <Button size="sm" variant="danger" onClick={() => onDelete(file)}>
          Delete
        </Button>
      </div>
    </div>
  );
}
```

**Task 1.2: Create VideoPlayer modal**

File: `frontend/src/components/media/VideoPlayer.tsx`

```tsx
/**
 * Modal video player for recordings and timelapses
 */

import { useEffect, useRef } from "react";
import { Modal } from "../Modal";
import type { MediaFile } from "./MediaCard";
import "./VideoPlayer.css";

interface VideoPlayerProps {
  file: MediaFile | null;
  isOpen: boolean;
  onClose: () => void;
}

export function VideoPlayer({ file, isOpen, onClose }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!isOpen && videoRef.current) {
      videoRef.current.pause();
    }
  }, [isOpen]);

  if (!file) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={file.filename} width="lg">
      <div className="video-player">
        <video
          ref={videoRef}
          src={file.path}
          controls
          autoPlay
          className="video-player__video"
        >
          Your browser does not support video playback.
        </video>
        <div className="video-player__info">
          <span>{file.size_human}</span>
          {file.duration_seconds && (
            <span>Duration: {Math.floor(file.duration_seconds)}s</span>
          )}
          {file.camera_name && <span>Camera: {file.camera_name}</span>}
        </div>
      </div>
    </Modal>
  );
}
```

**Task 1.3: Create ImageLightbox modal**

File: `frontend/src/components/media/ImageLightbox.tsx`

```tsx
/**
 * Lightbox modal for viewing still images
 */

import { Modal } from "../Modal";
import { Button } from "../Button";
import type { MediaFile } from "./MediaCard";
import "./ImageLightbox.css";

interface ImageLightboxProps {
  file: MediaFile | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ImageLightbox({ file, isOpen, onClose }: ImageLightboxProps) {
  if (!file) return null;

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = file.path;
    link.download = file.filename;
    link.click();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={file.filename} width="xl">
      <div className="image-lightbox">
        <img
          src={file.path}
          alt={file.filename}
          className="image-lightbox__image"
        />
        <div className="image-lightbox__info">
          <span>{file.size_human}</span>
          {file.width && file.height && (
            <span>{file.width} x {file.height}</span>
          )}
          {file.camera_name && <span>Camera: {file.camera_name}</span>}
          <Button variant="primary" onClick={handleDownload}>
            Download
          </Button>
        </div>
      </div>
    </Modal>
  );
}
```

### Phase 2: MediaBrowser Component

**Task 2.1: Create MediaBrowser**

File: `frontend/src/components/media/MediaBrowser.tsx`

```tsx
/**
 * Media browser component for listing and managing media files
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useToast } from "../../contexts/ToastContext";
import { Button } from "../Button";
import { ConfirmDialog } from "../ConfirmDialog";
import { MediaCard, type MediaFile } from "./MediaCard";
import { VideoPlayer } from "./VideoPlayer";
import { ImageLightbox } from "./ImageLightbox";
import "./MediaBrowser.css";

type MediaType = "recordings" | "stills" | "timelapses";
type SortBy = "created_at" | "size" | "name";
type SortOrder = "asc" | "desc";

interface MediaBrowserProps {
  mediaType: MediaType;
  cameraId?: number;
  limit?: number;
}

export function MediaBrowser({
  mediaType,
  cameraId,
  limit = 12,
}: MediaBrowserProps) {
  const [offset, setOffset] = useState(0);
  const [sortBy, setSortBy] = useState<SortBy>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [previewFile, setPreviewFile] = useState<MediaFile | null>(null);
  const [deleteFile, setDeleteFile] = useState<MediaFile | null>(null);

  const toast = useToast();
  const queryClient = useQueryClient();

  // Fetch files
  const { data, isLoading, error } = useQuery({
    queryKey: ["files", mediaType, cameraId, offset, sortBy, sortOrder],
    queryFn: async () => {
      const endpoint = `/api/v1/files/${mediaType}` as any;
      const response = await apiClient.GET(endpoint, {
        params: {
          query: {
            camera_id: cameraId,
            limit,
            offset,
            sort_by: sortBy,
            sort_order: sortOrder,
          },
        },
      });
      if (response.error) throw new Error("Failed to fetch files");
      return response.data as {
        files: MediaFile[];
        total: number;
        limit: number;
        offset: number;
      };
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (file: MediaFile) => {
      const response = await apiClient.DELETE(
        `/api/v1/files/${mediaType}/${file.filename}` as any
      );
      if (response.error) throw new Error("Failed to delete file");
    },
    onSuccess: () => {
      toast.success("File deleted successfully");
      queryClient.invalidateQueries({ queryKey: ["files", mediaType] });
      setDeleteFile(null);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to delete");
    },
  });

  const files = data?.files || [];
  const total = data?.total || 0;
  const hasMore = offset + limit < total;

  const handleLoadMore = () => {
    setOffset((prev) => prev + limit);
  };

  const handleSort = (newSortBy: SortBy) => {
    if (sortBy === newSortBy) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(newSortBy);
      setSortOrder("desc");
    }
    setOffset(0);
  };

  const handlePreview = (file: MediaFile) => {
    setPreviewFile(file);
  };

  const handleDelete = (file: MediaFile) => {
    setDeleteFile(file);
  };

  const confirmDelete = () => {
    if (deleteFile) {
      deleteMutation.mutate(deleteFile);
    }
  };

  const getTitle = () => {
    switch (mediaType) {
      case "recordings":
        return "Recordings";
      case "stills":
        return "Captured Images";
      case "timelapses":
        return "Timelapses";
    }
  };

  return (
    <div className="media-browser">
      <div className="media-browser__header">
        <h3 className="media-browser__title">{getTitle()}</h3>
        <div className="media-browser__controls">
          <span className="media-browser__count">
            {total} {total === 1 ? "file" : "files"}
          </span>
          <div className="media-browser__sort">
            <Button
              size="sm"
              variant={sortBy === "created_at" ? "primary" : "outline"}
              onClick={() => handleSort("created_at")}
            >
              Date {sortBy === "created_at" && (sortOrder === "desc" ? "↓" : "↑")}
            </Button>
            <Button
              size="sm"
              variant={sortBy === "size" ? "primary" : "outline"}
              onClick={() => handleSort("size")}
            >
              Size {sortBy === "size" && (sortOrder === "desc" ? "↓" : "↑")}
            </Button>
            <Button
              size="sm"
              variant={sortBy === "name" ? "primary" : "outline"}
              onClick={() => handleSort("name")}
            >
              Name {sortBy === "name" && (sortOrder === "desc" ? "↓" : "↑")}
            </Button>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="media-browser__loading">Loading files...</div>
      )}

      {error && (
        <div className="media-browser__error">
          Failed to load files. Please try again.
        </div>
      )}

      {!isLoading && !error && files.length === 0 && (
        <div className="media-browser__empty">
          No {mediaType} found.
        </div>
      )}

      {!isLoading && !error && files.length > 0 && (
        <>
          <div className="media-browser__grid">
            {files.map((file) => (
              <MediaCard
                key={file.filename}
                file={file}
                mediaType={mediaType}
                onPreview={handlePreview}
                onDelete={handleDelete}
              />
            ))}
          </div>

          {hasMore && (
            <div className="media-browser__load-more">
              <Button variant="outline" onClick={handleLoadMore}>
                Load More ({total - offset - limit} remaining)
              </Button>
            </div>
          )}
        </>
      )}

      {/* Video Player Modal */}
      {(mediaType === "recordings" || mediaType === "timelapses") && (
        <VideoPlayer
          file={previewFile}
          isOpen={previewFile !== null}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {/* Image Lightbox */}
      {mediaType === "stills" && (
        <ImageLightbox
          file={previewFile}
          isOpen={previewFile !== null}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={deleteFile !== null}
        title="Delete File"
        message={`Are you sure you want to delete "${deleteFile?.filename}"? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
        onConfirm={confirmDelete}
        onClose={() => setDeleteFile(null)}
      />
    </div>
  );
}
```

### Phase 3: Integration

**Task 3.1: Add MediaBrowser to RecordTab**

Update `frontend/src/components/camera/RecordTab.tsx`:

```tsx
import { MediaBrowser } from "../media/MediaBrowser";

// In the component, after recording controls:
<div className="record-tab__history">
  <MediaBrowser mediaType="recordings" cameraId={cameraId} limit={6} />
</div>
```

**Task 3.2: Add MediaBrowser to CaptureTab**

Update `frontend/src/components/camera/CaptureTab.tsx`:

```tsx
import { MediaBrowser } from "../media/MediaBrowser";

// In the component, after capture controls:
<div className="capture-tab__history">
  <MediaBrowser mediaType="stills" cameraId={cameraId} limit={8} />
</div>
```

**Task 3.3: Add MediaBrowser to TimelapseTab**

Update `frontend/src/components/camera/TimelapseTab.tsx`:

```tsx
import { MediaBrowser } from "../media/MediaBrowser";

// In the component, after timelapse controls:
<div className="timelapse-tab__history">
  <MediaBrowser mediaType="timelapses" cameraId={cameraId} limit={6} />
</div>
```

### Phase 4: Styling

**Task 4.1: Create CSS files**

Key styles needed:
- Grid layout for media cards (responsive)
- Card hover effects
- Play overlay for videos
- Thumbnail lazy loading placeholder
- Sort buttons active state
- Load more button
- Video player fullscreen support
- Image lightbox zoom

---

## CSS Example

File: `frontend/src/components/media/MediaBrowser.css`

```css
.media-browser {
  margin-top: 2rem;
  border-top: 1px solid var(--border-color);
  padding-top: 1.5rem;
}

.media-browser__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.media-browser__title {
  margin: 0;
  font-size: 1.1rem;
}

.media-browser__controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.media-browser__sort {
  display: flex;
  gap: 0.25rem;
}

.media-browser__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.media-browser__load-more {
  text-align: center;
  margin-top: 1.5rem;
}

.media-browser__empty,
.media-browser__loading,
.media-browser__error {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .media-browser__grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
```

---

## Testing Checklist

- [ ] Files load correctly for each media type
- [ ] Pagination works (load more)
- [ ] Sorting works (date, size, name)
- [ ] Camera filter works when cameraId provided
- [ ] Video playback works in modal
- [ ] Image preview works in lightbox
- [ ] Download works for all file types
- [ ] Delete shows confirmation dialog
- [ ] Delete removes file and refreshes list
- [ ] Empty state shows when no files
- [ ] Loading state shows while fetching
- [ ] Error state shows on API failure
- [ ] Responsive layout works on mobile

---

**Status**: `.ready.md` - Ready for implementation (after Files API backend)
