/**
 * Full-screen media viewer for observations.
 * Supports images with pinch-to-zoom and videos with playback controls.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { ConfirmDialog } from "../ConfirmDialog";
import type { CompletedObservation } from "../../hooks/useObservations";
import { getMediaUrl, useDeleteObservation } from "../../hooks/useObservations";
import "./MediaViewer.css";

interface MediaViewerProps {
  observation: CompletedObservation;
  observations: CompletedObservation[];
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export function MediaViewer({
  observation,
  observations,
  currentIndex,
  onClose,
  onNavigate,
}: MediaViewerProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastTouchRef = useRef<{ time: number; x: number; y: number } | null>(null);
  const pinchRef = useRef<{ startDistance: number; startScale: number } | null>(null);

  const deleteMutation = useDeleteObservation();

  const mediaUrl = getMediaUrl(observation.id);
  const isVideo = observation.observation_type === "recording" || observation.observation_type === "timelapse";

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < observations.length - 1;

  // Navigate to previous observation
  const handlePrev = useCallback(() => {
    if (hasPrev) {
      resetZoom();
      onNavigate(currentIndex - 1);
    }
  }, [currentIndex, hasPrev, onNavigate]);

  // Navigate to next observation
  const handleNext = useCallback(() => {
    if (hasNext) {
      resetZoom();
      onNavigate(currentIndex + 1);
    }
  }, [currentIndex, hasNext, onNavigate]);

  // Reset zoom state
  const resetZoom = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setIsZoomed(false);
  }, []);

  // Handle zoom change
  const handleZoom = useCallback((newScale: number, centerX?: number, centerY?: number) => {
    const clampedScale = Math.max(1, Math.min(5, newScale));

    if (clampedScale === 1) {
      resetZoom();
      return;
    }

    setScale(clampedScale);
    setIsZoomed(clampedScale > 1);

    // Adjust position to zoom towards center point
    if (centerX !== undefined && centerY !== undefined && imageRef.current && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();

      // Calculate new position to keep the zoom centered on the point
      const relativeX = (centerX - rect.width / 2) / scale;
      const relativeY = (centerY - rect.height / 2) / scale;

      const newX = position.x - relativeX * (clampedScale / scale - 1);
      const newY = position.y - relativeY * (clampedScale / scale - 1);

      setPosition({ x: newX, y: newY });
    }
  }, [scale, position, resetZoom]);

  // Handle mouse wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (isVideo) return;

    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      handleZoom(scale * delta, e.clientX - rect.left, e.clientY - rect.top);
    }
  }, [scale, isVideo, handleZoom]);

  // Handle touch start
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (isVideo) return;

    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const now = Date.now();

      // Double tap to zoom
      if (lastTouchRef.current) {
        const timeDiff = now - lastTouchRef.current.time;
        const distX = Math.abs(touch.clientX - lastTouchRef.current.x);
        const distY = Math.abs(touch.clientY - lastTouchRef.current.y);

        if (timeDiff < 300 && distX < 30 && distY < 30) {
          e.preventDefault();
          const rect = containerRef.current?.getBoundingClientRect();
          if (rect) {
            if (isZoomed) {
              resetZoom();
            } else {
              handleZoom(2, touch.clientX - rect.left, touch.clientY - rect.top);
            }
          }
          lastTouchRef.current = null;
          return;
        }
      }

      lastTouchRef.current = { time: now, x: touch.clientX, y: touch.clientY };

      // Start drag if zoomed
      if (isZoomed) {
        setIsDragging(true);
        setDragStart({ x: touch.clientX - position.x, y: touch.clientY - position.y });
      }
    } else if (e.touches.length === 2) {
      // Pinch start
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );
      pinchRef.current = { startDistance: distance, startScale: scale };
    }
  }, [isVideo, isZoomed, position, scale, handleZoom, resetZoom]);

  // Handle touch move
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (isVideo) return;

    if (e.touches.length === 1 && isDragging) {
      e.preventDefault();
      const touch = e.touches[0];
      setPosition({
        x: touch.clientX - dragStart.x,
        y: touch.clientY - dragStart.y,
      });
    } else if (e.touches.length === 2 && pinchRef.current) {
      e.preventDefault();
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      const pinchScale = distance / pinchRef.current.startDistance;
      const newScale = pinchRef.current.startScale * pinchScale;

      // Calculate center point of the pinch
      const centerX = (touch1.clientX + touch2.clientX) / 2;
      const centerY = (touch1.clientY + touch2.clientY) / 2;
      const rect = containerRef.current?.getBoundingClientRect();

      if (rect) {
        handleZoom(newScale, centerX - rect.left, centerY - rect.top);
      }
    }
  }, [isVideo, isDragging, dragStart, handleZoom]);

  // Handle touch end
  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    pinchRef.current = null;
  }, []);

  // Handle mouse drag for desktop
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isVideo || !isZoomed) return;
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  }, [isVideo, isZoomed, position]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowLeft":
          handlePrev();
          break;
        case "ArrowRight":
          handleNext();
          break;
        case "Escape":
          if (isZoomed) {
            resetZoom();
          } else {
            onClose();
          }
          break;
        case "+":
        case "=":
          handleZoom(scale * 1.2);
          break;
        case "-":
          handleZoom(scale / 1.2);
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePrev, handleNext, onClose, isZoomed, resetZoom, scale, handleZoom]);

  // Handle download
  const handleDownload = useCallback(() => {
    const link = document.createElement("a");
    link.href = mediaUrl;
    link.download = `observation_${observation.id}_${observation.observation_type}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [mediaUrl, observation]);

  // Handle delete
  const handleDelete = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  const confirmDelete = useCallback(() => {
    deleteMutation.mutate(observation.id, {
      onSuccess: () => {
        setShowDeleteConfirm(false);
        // Navigate to prev or next, or close if last
        if (observations.length <= 1) {
          onClose();
        } else if (hasNext) {
          onNavigate(currentIndex);
        } else {
          onNavigate(currentIndex - 1);
        }
      },
    });
  }, [deleteMutation, observation.id, observations.length, onClose, hasNext, onNavigate, currentIndex]);

  return (
    <div className="media-viewer">
      <div className="media-viewer__backdrop" onClick={onClose} />

      {/* Header with controls */}
      <div className="media-viewer__header">
        <div className="media-viewer__title">
          <span className="media-viewer__camera">{observation.camera_name}</span>
          <span className="media-viewer__type">{observation.observation_type}</span>
        </div>
        <div className="media-viewer__controls">
          {!isVideo && (
            <>
              <button
                className="media-viewer__btn"
                onClick={() => handleZoom(scale * 1.2)}
                title="Zoom in"
              >
                +
              </button>
              <button
                className="media-viewer__btn"
                onClick={() => handleZoom(scale / 1.2)}
                title="Zoom out"
              >
                -
              </button>
              {isZoomed && (
                <button
                  className="media-viewer__btn"
                  onClick={resetZoom}
                  title="Reset zoom"
                >
                  1:1
                </button>
              )}
            </>
          )}
          <button
            className="media-viewer__btn"
            onClick={handleDownload}
            title="Download"
          >
            Download
          </button>
          <button
            className="media-viewer__btn media-viewer__btn--danger"
            onClick={handleDelete}
            title="Delete"
          >
            Delete
          </button>
          <button
            className="media-viewer__btn media-viewer__btn--close"
            onClick={onClose}
            title="Close"
          >
            Close
          </button>
        </div>
      </div>

      {/* Navigation arrows */}
      {hasPrev && (
        <button
          className="media-viewer__nav media-viewer__nav--prev"
          onClick={handlePrev}
          aria-label="Previous"
        >
          &lt;
        </button>
      )}
      {hasNext && (
        <button
          className="media-viewer__nav media-viewer__nav--next"
          onClick={handleNext}
          aria-label="Next"
        >
          &gt;
        </button>
      )}

      {/* Media content */}
      <div
        ref={containerRef}
        className={`media-viewer__content ${isZoomed ? "media-viewer__content--zoomed" : ""}`}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {isVideo ? (
          <video
            key={observation.id}
            src={mediaUrl}
            controls
            autoPlay
            className="media-viewer__video"
          />
        ) : (
          <img
            ref={imageRef}
            key={observation.id}
            src={mediaUrl}
            alt={`${observation.observation_type} from ${observation.camera_name}`}
            className="media-viewer__image"
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              cursor: isZoomed ? (isDragging ? "grabbing" : "grab") : "default",
            }}
            draggable={false}
          />
        )}
      </div>

      {/* Footer with info */}
      <div className="media-viewer__footer">
        <span className="media-viewer__counter">
          {currentIndex + 1} / {observations.length}
        </span>
        <span className="media-viewer__date">
          {new Date(observation.started_at).toLocaleString()}
        </span>
        <span className="media-viewer__size">{observation.size_display}</span>
      </div>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDelete}
        title="Delete Observation"
        message={`Are you sure you want to delete this ${observation.observation_type}? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
