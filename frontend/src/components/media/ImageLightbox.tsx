/**
 * Lightbox modal for viewing still images
 */

import { Modal } from "../Modal";
import { Button } from "../Button";
import type { MediaFile } from "./VideoPlayer";
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

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={file.filename} width="xl">
      <div className="image-lightbox">
        <div className="image-lightbox__container">
          <img
            src={file.path}
            alt={file.filename}
            className="image-lightbox__image"
          />
        </div>
        <div className="image-lightbox__info">
          <span className="image-lightbox__meta">{file.size_display}</span>
          <span className="image-lightbox__meta">{formatDate(file.created_at)}</span>
          <Button variant="primary" size="sm" onClick={handleDownload}>
            Download
          </Button>
        </div>
      </div>
    </Modal>
  );
}
