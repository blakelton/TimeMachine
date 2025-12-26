/**
 * API exports.
 *
 * Re-exports the typed API client and all typed wrappers.
 */

// Core client
export { apiClient, setAuthHeader, clearAuthHeader, hasAuth } from "./client";

// Camera API wrappers
export {
  captureImage,
  startPreview,
  stopPreview,
  getPreviewStatus,
  startRecording,
  stopRecording,
  getRecordingStatus,
  startTimelapse,
  stopTimelapse,
  getTimelapseStatus,
  checkCameraHealth,
  getCamera,
  updateCamera,
  deleteCamera,
} from "./camera";

// Observation API wrappers
export {
  startObservation,
  getActiveObservationByCamera,
  getObservation,
  getObservationStatus,
  stopObservation,
  deleteObservation,
  updateObservationNotes,
  getObservationThumbnail,
  getObservationPreview,
  generateObservationPreview,
  getObservationMedia,
  batchDeleteObservations,
  listActiveObservations,
  listCompletedObservations,
} from "./observations";
