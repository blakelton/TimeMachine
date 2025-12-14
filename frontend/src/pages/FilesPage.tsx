/**
 * Files page for browsing and managing all stored media
 */

import { useState, useEffect } from "react";
import { FileBrowser } from "../components/storage/FileBrowser";
import "./FilesPage.css";

interface StorageStats {
  total_files: number;
  total_size_bytes: number;
  total_size_display: string;
  recordings: { count: number; size_display: string };
  stills: { count: number; size_display: string };
  timelapse: { count: number; size_display: string };
  disk: {
    free_display: string;
    percent_used: number;
  } | null;
}

export function FilesPage() {
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch("/api/v1/storage/stats");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch storage stats:", err);
    } finally {
      setIsLoadingStats(false);
    }
  };

  return (
    <div className="files-page">
      <div className="files-page__header">
        <h1>Files</h1>
        <p className="files-page__subtitle">Browse and manage stored media</p>
      </div>

      {stats && (
        <div className="files-page__stats">
          <div className="files-page__stat-card">
            <div className="files-page__stat-value">{stats.total_files}</div>
            <div className="files-page__stat-label">Total Files</div>
          </div>
          <div className="files-page__stat-card">
            <div className="files-page__stat-value">{stats.total_size_display}</div>
            <div className="files-page__stat-label">Total Size</div>
          </div>
          <div className="files-page__stat-card">
            <div className="files-page__stat-value">{stats.recordings.count}</div>
            <div className="files-page__stat-label">Recordings ({stats.recordings.size_display})</div>
          </div>
          <div className="files-page__stat-card">
            <div className="files-page__stat-value">{stats.stills.count}</div>
            <div className="files-page__stat-label">Stills ({stats.stills.size_display})</div>
          </div>
          {stats.disk && (
            <div className="files-page__stat-card">
              <div className="files-page__stat-value">{stats.disk.free_display}</div>
              <div className="files-page__stat-label">
                Free Space ({(100 - stats.disk.percent_used).toFixed(0)}%)
              </div>
            </div>
          )}
        </div>
      )}

      <div className="files-page__browser">
        <FileBrowser limit={25} showTypeFilter showDelete />
      </div>
    </div>
  );
}
