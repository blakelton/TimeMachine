/**
 * Modal video player for recordings and timelapses
 */

import { useEffect, useRef } from "react";
import { Modal } from "../Modal";
import { Button } from "../Button";
import "./VideoPlayer.css";

export interface MediaFile {
  filename: string;
  path: string;
  size_bytes: number;
  size_display: string;
  file_type: string;
  camera_id: number | null;
  created_at: string;
}

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

  const handleDownload = () => {
    window.open(file.path, "_blank");
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

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
          <span className="video-player__meta">{file.size_display}</span>
          <span className="video-player__meta">{formatDate(file.created_at)}</span>
          <Button variant="primary" size="sm" onClick={handleDownload}>
            Download
          </Button>
        </div>
      </div>
    </Modal>
  );
}
