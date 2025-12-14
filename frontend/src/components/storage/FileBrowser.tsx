/**
 * File browser component for viewing and managing stored files
 */

import { useState, useEffect } from "react";
import { apiClient } from "../../api/client";
import { Button } from "../Button";
import { useToast } from "../../contexts/ToastContext";
import { VideoPlayer, type MediaFile } from "../media/VideoPlayer";
import { ImageLightbox } from "../media/ImageLightbox";
import "./FileBrowser.css";

interface StoredFile {
  file_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  size_display: string;
  created_at: string;
  camera_id: number | null;
  download_url: string;
}

interface FileBrowserProps {
  cameraId?: number;
  fileType?: "recording" | "still" | "timelapse";
  limit?: number;
  showTypeFilter?: boolean;
  showDelete?: boolean;
}

export function FileBrowser({
  cameraId,
  fileType,
  limit = 20,
  showTypeFilter = true,
  showDelete = true,
}: FileBrowserProps) {
  const [files, setFiles] = useState<StoredFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | undefined>(fileType);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [previewFile, setPreviewFile] = useState<MediaFile | null>(null);
  const [previewType, setPreviewType] = useState<"video" | "image" | null>(null);
  const toast = useToast();

  const fetchFiles = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params: Record<string, any> = {
        limit,
        offset,
      };
      if (selectedType) params.file_type = selectedType;
      if (cameraId) params.camera_id = cameraId;

      const response = await fetch(
        `/api/v1/storage/files?${new URLSearchParams(params)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.statusText}`);
      }

      const data = await response.json();
      setFiles(data.files);
      setTotal(data.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load files";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [selectedType, offset, cameraId]);

  const handleDownload = (file: StoredFile) => {
    const link = document.createElement("a");
    link.href = file.download_url;
    link.download = file.filename;
    link.click();
  };

  const handlePreview = (file: StoredFile) => {
    const mediaFile: MediaFile = {
      filename: file.filename,
      path: file.download_url,
      size_bytes: file.size_bytes,
      size_display: file.size_display,
      file_type: file.file_type,
      camera_id: file.camera_id,
      created_at: file.created_at,
    };
    setPreviewFile(mediaFile);

    if (file.file_type === "still") {
      setPreviewType("image");
    } else {
      setPreviewType("video");
    }
  };

  const closePreview = () => {
    setPreviewFile(null);
    setPreviewType(null);
  };

  const handleDelete = async (file: StoredFile) => {
    if (!confirm(`Delete ${file.filename}?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/storage/files/${file.file_id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete file");
      }

      toast.success(`Deleted ${file.filename}`);
      fetchFiles();
    } catch (err) {
      toast.error("Failed to delete file");
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "recording":
        return "🎬";
      case "still":
        return "📷";
      case "timelapse":
        return "⏱️";
      default:
        return "📄";
    }
  };

  const hasMore = offset + files.length < total;
  const hasPrev = offset > 0;

  return (
    <div className="file-browser">
      {showTypeFilter && (
        <div className="file-browser__filters">
          <select
            value={selectedType || ""}
            onChange={(e) => {
              setSelectedType(e.target.value || undefined);
              setOffset(0);
            }}
            className="file-browser__type-select"
          >
            <option value="">All Types</option>
            <option value="recording">Recordings</option>
            <option value="still">Still Images</option>
            <option value="timelapse">Timelapse</option>
          </select>
          <Button variant="secondary" onClick={fetchFiles} disabled={isLoading}>
            Refresh
          </Button>
        </div>
      )}

      {isLoading && <div className="file-browser__loading">Loading files...</div>}

      {error && <div className="file-browser__error">{error}</div>}

      {!isLoading && !error && files.length === 0 && (
        <div className="file-browser__empty">No files found</div>
      )}

      {!isLoading && !error && files.length > 0 && (
        <>
          <div className="file-browser__list">
            {files.map((file) => (
              <div key={file.file_id} className="file-browser__item">
                <div className="file-browser__item-icon">
                  {getTypeIcon(file.file_type)}
                </div>
                <div className="file-browser__item-info">
                  <div className="file-browser__item-name">{file.filename}</div>
                  <div className="file-browser__item-meta">
                    <span>{formatDate(file.created_at)}</span>
                    <span>{file.size_display}</span>
                    {file.camera_id && <span>Camera {file.camera_id}</span>}
                  </div>
                </div>
                <div className="file-browser__item-actions">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handlePreview(file)}
                  >
                    {file.file_type === "still" ? "View" : "Play"}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleDownload(file)}
                  >
                    Download
                  </Button>
                  {showDelete && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(file)}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="file-browser__pagination">
            <Button
              variant="secondary"
              disabled={!hasPrev}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              Previous
            </Button>
            <span className="file-browser__page-info">
              {offset + 1} - {Math.min(offset + files.length, total)} of {total}
            </span>
            <Button
              variant="secondary"
              disabled={!hasMore}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </Button>
          </div>
        </>
      )}

      {/* Video Player Modal */}
      <VideoPlayer
        file={previewFile}
        isOpen={previewType === "video"}
        onClose={closePreview}
      />

      {/* Image Lightbox Modal */}
      <ImageLightbox
        file={previewFile}
        isOpen={previewType === "image"}
        onClose={closePreview}
      />
    </div>
  );
}
