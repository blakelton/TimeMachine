# Camera System - Plan

## Overview

Implement camera device discovery, abstraction layer, GStreamer pipelines, and streaming/capture/recording services. This is the core of the observation chamber system.

**Dependencies**: 01-backend-foundation, 02-database-config
**Estimated Duration**: 4-5 days

---

## Phase 1: Device Discovery

### Goal
Enumerate and identify CSI and USB cameras with capability detection.

### Tasks

1. **Add dependencies to `requirements.txt`**
   ```
   picamera2>=0.3.12
   # GStreamer via system packages (python3-gi, gstreamer1.0-plugins-*)
   ```

2. **Create `app/services/camera/discovery.py`**
   ```python
   import subprocess
   import re
   from pathlib import Path
   from dataclasses import dataclass
   from typing import Literal
   import structlog

   logger = structlog.get_logger(__name__)

   @dataclass
   class CameraCapability:
       width: int
       height: int
       fps: list[int]
       formats: list[str]

   @dataclass
   class DiscoveredCamera:
       device_path: str
       source_type: Literal["CSI", "USB"]
       name: str
       capabilities: list[CameraCapability]

   def discover_csi_cameras() -> list[DiscoveredCamera]:
       """Discover CSI cameras via libcamera."""
       cameras = []
       try:
           result = subprocess.run(
               ["libcamera-hello", "--list-cameras"],
               capture_output=True,
               text=True,
               timeout=5,
           )
           # Parse output for camera info
           # Format: "0 : imx219 [3280x2464]..."
           for match in re.finditer(r"(\d+)\s*:\s*(\w+)", result.stdout):
               idx, name = match.groups()
               cameras.append(DiscoveredCamera(
                   device_path=f"csi:{idx}",
                   source_type="CSI",
                   name=f"CSI-{name}",
                   capabilities=[
                       CameraCapability(1920, 1080, [30], ["MJPEG", "H264"]),
                       CameraCapability(1280, 720, [60, 30], ["MJPEG", "H264"]),
                   ],
               ))
       except Exception as e:
           logger.warning("csi_discovery_failed", error=str(e))
       return cameras

   def discover_usb_cameras() -> list[DiscoveredCamera]:
       """Discover USB cameras via V4L2."""
       cameras = []
       video_devices = list(Path("/dev").glob("video*"))

       for device in video_devices:
           try:
               # Get device capabilities using v4l2-ctl
               result = subprocess.run(
                   ["v4l2-ctl", "-d", str(device), "--all"],
                   capture_output=True,
                   text=True,
                   timeout=5,
               )
               if "Video Capture" not in result.stdout:
                   continue

               # Extract device name
               name_match = re.search(r"Card type\s*:\s*(.+)", result.stdout)
               name = name_match.group(1).strip() if name_match else device.name

               # Get supported formats
               formats_result = subprocess.run(
                   ["v4l2-ctl", "-d", str(device), "--list-formats-ext"],
                   capture_output=True,
                   text=True,
                   timeout=5,
               )

               capabilities = parse_v4l2_formats(formats_result.stdout)

               cameras.append(DiscoveredCamera(
                   device_path=str(device),
                   source_type="USB",
                   name=name,
                   capabilities=capabilities,
               ))
           except Exception as e:
               logger.warning("usb_discovery_failed", device=str(device), error=str(e))

       return cameras

   def parse_v4l2_formats(output: str) -> list[CameraCapability]:
       """Parse v4l2-ctl --list-formats-ext output."""
       capabilities = []
       current_format = None
       
       for line in output.split("\n"):
           if "MJPG" in line or "YUYV" in line or "H264" in line:
               current_format = "MJPEG" if "MJPG" in line else "H264" if "H264" in line else "YUYV"
           elif "Size:" in line and current_format:
               match = re.search(r"(\d+)x(\d+)", line)
               if match:
                   w, h = int(match.group(1)), int(match.group(2))
                   # Default fps if not parsed
                   capabilities.append(CameraCapability(w, h, [30], [current_format]))
       
       return capabilities or [CameraCapability(640, 480, [30], ["MJPEG"])]

   async def discover_all_cameras() -> list[DiscoveredCamera]:
       """Discover all available cameras."""
       import asyncio
       loop = asyncio.get_event_loop()
       
       csi = await loop.run_in_executor(None, discover_csi_cameras)
       usb = await loop.run_in_executor(None, discover_usb_cameras)
       
       return csi + usb
   ```

### Acceptance Criteria
- [ ] CSI cameras detected via libcamera
- [ ] USB cameras detected via V4L2
- [ ] Capabilities (resolution, fps) extracted
- [ ] Discovery is non-blocking

---

## Phase 2: Camera Abstraction Layer

### Goal
Create unified interface for CSI and USB cameras.

### Tasks

1. **Create `app/services/camera/base.py`**
   ```python
   from abc import ABC, abstractmethod
   from dataclasses import dataclass
   from typing import Optional, AsyncIterator
   import numpy as np

   @dataclass
   class CameraConfig:
       device_path: str
       resolution: tuple[int, int]
       fps: int
       format: str = "MJPEG"

   @dataclass
   class Frame:
       data: bytes
       width: int
       height: int
       timestamp: float
       format: str

   class CameraSource(ABC):
       def __init__(self, config: CameraConfig):
           self.config = config
           self._running = False

       @abstractmethod
       async def open(self) -> bool:
           """Open camera connection."""
           pass

       @abstractmethod
       async def close(self) -> None:
           """Release camera resources."""
           pass

       @abstractmethod
       async def capture_frame(self) -> Optional[Frame]:
           """Capture a single frame."""
           pass

       @abstractmethod
       def stream_frames(self) -> AsyncIterator[Frame]:
           """Stream frames continuously."""
           pass

       @property
       def is_open(self) -> bool:
           return self._running
   ```

2. **Create `app/services/camera/csi.py`**
   ```python
   from typing import Optional, AsyncIterator
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   import time
   import structlog

   from app.services.camera.base import CameraSource, CameraConfig, Frame

   logger = structlog.get_logger(__name__)
   _executor = ThreadPoolExecutor(max_workers=2)

   class CSICamera(CameraSource):
       def __init__(self, config: CameraConfig):
           super().__init__(config)
           self._picam2 = None

       async def open(self) -> bool:
           try:
               from picamera2 import Picamera2
               
               loop = asyncio.get_event_loop()
               
               def _init():
                   cam_idx = int(self.config.device_path.split(":")[1])
                   picam2 = Picamera2(cam_idx)
                   config = picam2.create_still_configuration(
                       main={"size": self.config.resolution}
                   )
                   picam2.configure(config)
                   picam2.start()
                   return picam2

               self._picam2 = await loop.run_in_executor(_executor, _init)
               self._running = True
               logger.info("csi_camera_opened", device=self.config.device_path)
               return True
           except Exception as e:
               logger.error("csi_camera_open_failed", error=str(e))
               return False

       async def close(self) -> None:
           if self._picam2:
               loop = asyncio.get_event_loop()
               await loop.run_in_executor(_executor, self._picam2.stop)
               self._picam2 = None
           self._running = False
           logger.info("csi_camera_closed", device=self.config.device_path)

       async def capture_frame(self) -> Optional[Frame]:
           if not self._picam2:
               return None
           
           loop = asyncio.get_event_loop()
           
           def _capture():
               import io
               from PIL import Image
               
               array = self._picam2.capture_array()
               img = Image.fromarray(array)
               buffer = io.BytesIO()
               img.save(buffer, format="JPEG", quality=85)
               return buffer.getvalue()

           try:
               data = await loop.run_in_executor(_executor, _capture)
               return Frame(
                   data=data,
                   width=self.config.resolution[0],
                   height=self.config.resolution[1],
                   timestamp=time.time(),
                   format="JPEG",
               )
           except Exception as e:
               logger.error("csi_capture_failed", error=str(e))
               return None

       async def stream_frames(self) -> AsyncIterator[Frame]:
           while self._running:
               frame = await self.capture_frame()
               if frame:
                   yield frame
               await asyncio.sleep(1.0 / self.config.fps)
   ```

3. **Create `app/services/camera/usb.py`**
   ```python
   from typing import Optional, AsyncIterator
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   import time
   import structlog

   from app.services.camera.base import CameraSource, CameraConfig, Frame

   logger = structlog.get_logger(__name__)
   _executor = ThreadPoolExecutor(max_workers=4)

   class USBCamera(CameraSource):
       def __init__(self, config: CameraConfig):
           super().__init__(config)
           self._cap = None

       async def open(self) -> bool:
           try:
               import cv2
               
               loop = asyncio.get_event_loop()
               
               def _init():
                   cap = cv2.VideoCapture(self.config.device_path)
                   cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
                   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
                   cap.set(cv2.CAP_PROP_FPS, self.config.fps)
                   return cap if cap.isOpened() else None

               self._cap = await loop.run_in_executor(_executor, _init)
               if self._cap:
                   self._running = True
                   logger.info("usb_camera_opened", device=self.config.device_path)
                   return True
               return False
           except Exception as e:
               logger.error("usb_camera_open_failed", error=str(e))
               return False

       async def close(self) -> None:
           if self._cap:
               loop = asyncio.get_event_loop()
               await loop.run_in_executor(_executor, self._cap.release)
               self._cap = None
           self._running = False
           logger.info("usb_camera_closed", device=self.config.device_path)

       async def capture_frame(self) -> Optional[Frame]:
           if not self._cap:
               return None
           
           import cv2
           loop = asyncio.get_event_loop()
           
           def _capture():
               ret, frame = self._cap.read()
               if not ret:
                   return None
               _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
               return buffer.tobytes()

           try:
               data = await loop.run_in_executor(_executor, _capture)
               if data:
                   return Frame(
                       data=data,
                       width=self.config.resolution[0],
                       height=self.config.resolution[1],
                       timestamp=time.time(),
                       format="JPEG",
                   )
               return None
           except Exception as e:
               logger.error("usb_capture_failed", error=str(e))
               return None

       async def stream_frames(self) -> AsyncIterator[Frame]:
           while self._running:
               frame = await self.capture_frame()
               if frame:
                   yield frame
               else:
                   await asyncio.sleep(0.1)  # Back off on error
   ```

### Acceptance Criteria
- [ ] CSI and USB cameras use same interface
- [ ] Non-blocking frame capture
- [ ] Clean resource release on close

---

## Phase 3: GStreamer Pipelines

### Goal
Build efficient pipelines for preview, recording, and capture.

### Tasks

1. **Create `app/services/camera/pipeline.py`**
   ```python
   from dataclasses import dataclass
   from typing import Optional
   import structlog

   logger = structlog.get_logger(__name__)

   @dataclass
   class PipelineConfig:
       device_path: str
       width: int = 1920
       height: int = 1080
       fps: int = 30
       bitrate: int = 4000000
       profile: str = "main"

   class GStreamerPipeline:
       """GStreamer pipeline builder for hardware-accelerated encoding."""

       @staticmethod
       def preview_pipeline(config: PipelineConfig) -> str:
           """MJPEG preview pipeline for web streaming."""
           if config.device_path.startswith("csi:"):
               return (
                   f"libcamerasrc camera-name=/base/soc/i2c0mux/i2c@1/imx219@10 ! "
                   f"video/x-raw,width={config.width},height={config.height},framerate={config.fps}/1 ! "
                   f"jpegenc quality=75 ! "
                   f"appsink name=sink emit-signals=true max-buffers=2 drop=true"
               )
           else:
               return (
                   f"v4l2src device={config.device_path} ! "
                   f"video/x-raw,width={config.width},height={config.height},framerate={config.fps}/1 ! "
                   f"jpegenc quality=75 ! "
                   f"appsink name=sink emit-signals=true max-buffers=2 drop=true"
               )

       @staticmethod
       def recording_pipeline(config: PipelineConfig, output_path: str) -> str:
           """H.264 recording pipeline using hardware encoder."""
           # v4l2h264enc is the Pi 3 hardware encoder
           if config.device_path.startswith("csi:"):
               return (
                   f"libcamerasrc camera-name=/base/soc/i2c0mux/i2c@1/imx219@10 ! "
                   f"video/x-raw,width={config.width},height={config.height},framerate={config.fps}/1 ! "
                   f"v4l2h264enc extra-controls=\"encode,video_bitrate={config.bitrate}\" ! "
                   f"video/x-h264,profile={config.profile} ! "
                   f"h264parse ! "
                   f"mp4mux ! "
                   f"filesink location={output_path}"
               )
           else:
               return (
                   f"v4l2src device={config.device_path} ! "
                   f"video/x-raw,width={config.width},height={config.height},framerate={config.fps}/1 ! "
                   f"v4l2h264enc extra-controls=\"encode,video_bitrate={config.bitrate}\" ! "
                   f"video/x-h264,profile={config.profile} ! "
                   f"h264parse ! "
                   f"mp4mux ! "
                   f"filesink location={output_path}"
               )

       @staticmethod
       def still_capture_pipeline(config: PipelineConfig) -> str:
           """Single frame JPEG capture."""
           if config.device_path.startswith("csi:"):
               return (
                   f"libcamerasrc camera-name=/base/soc/i2c0mux/i2c@1/imx219@10 ! "
                   f"video/x-raw,width={config.width},height={config.height} ! "
                   f"jpegenc quality=95 ! "
                   f"appsink name=sink emit-signals=true max-buffers=1"
               )
           else:
               return (
                   f"v4l2src device={config.device_path} num-buffers=1 ! "
                   f"video/x-raw,width={config.width},height={config.height} ! "
                   f"jpegenc quality=95 ! "
                   f"appsink name=sink"
               )
   ```

### Acceptance Criteria
- [ ] Preview pipeline < 500ms latency
- [ ] Recording uses v4l2h264enc
- [ ] Pipelines work for both CSI and USB

---

## Phase 4: Stream Management

### Goal
Manage concurrent streams with proper resource limits.

### Tasks

1. **Create `app/services/camera/manager.py`**
   ```python
   from typing import Dict, Optional
   import asyncio
   import structlog

   from app.services.camera.base import CameraSource, CameraConfig
   from app.services.camera.csi import CSICamera
   from app.services.camera.usb import USBCamera

   logger = structlog.get_logger(__name__)

   class CameraManager:
       MAX_CONCURRENT_STREAMS = 2
       MAX_CONCURRENT_RECORDINGS = 1

       def __init__(self):
           self._cameras: Dict[int, CameraSource] = {}
           self._active_streams: set[int] = set()
           self._active_recordings: set[int] = set()
           self._lock = asyncio.Lock()

       def _create_camera(self, camera_id: int, config: CameraConfig) -> CameraSource:
           if config.device_path.startswith("csi:"):
               return CSICamera(config)
           else:
               return USBCamera(config)

       async def open_camera(self, camera_id: int, config: CameraConfig) -> bool:
           async with self._lock:
               if camera_id in self._cameras:
                   return True
               
               camera = self._create_camera(camera_id, config)
               if await camera.open():
                   self._cameras[camera_id] = camera
                   return True
               return False

       async def close_camera(self, camera_id: int) -> None:
           async with self._lock:
               if camera_id in self._cameras:
                   await self._cameras[camera_id].close()
                   del self._cameras[camera_id]
                   self._active_streams.discard(camera_id)
                   self._active_recordings.discard(camera_id)

       async def start_stream(self, camera_id: int) -> bool:
           if len(self._active_streams) >= self.MAX_CONCURRENT_STREAMS:
               logger.warning("max_streams_reached")
               return False
           
           if camera_id not in self._cameras:
               return False
           
           self._active_streams.add(camera_id)
           return True

       async def stop_stream(self, camera_id: int) -> None:
           self._active_streams.discard(camera_id)

       async def start_recording(self, camera_id: int) -> bool:
           if len(self._active_recordings) >= self.MAX_CONCURRENT_RECORDINGS:
               logger.warning("max_recordings_reached")
               return False
           
           self._active_recordings.add(camera_id)
           return True

       async def stop_recording(self, camera_id: int) -> None:
           self._active_recordings.discard(camera_id)

       def get_camera(self, camera_id: int) -> Optional[CameraSource]:
           return self._cameras.get(camera_id)

   # Singleton instance
   camera_manager = CameraManager()
   ```

### Acceptance Criteria
- [ ] Limits enforced (2 streams, 1 recording)
- [ ] Thread-safe operations
- [ ] Clean resource tracking

---

## Phase 5: Recording & Capture Services

### Goal
Implement capture and recording with proper file management.

### Tasks

1. **Create `app/services/camera/capture.py`**
   ```python
   from pathlib import Path
   from datetime import datetime
   import structlog

   from app.services.camera.manager import camera_manager

   logger = structlog.get_logger(__name__)

   class CaptureService:
       def __init__(self, stills_path: str):
           self.stills_path = Path(stills_path)
           self.stills_path.mkdir(parents=True, exist_ok=True)

       def _generate_filename(self, camera_id: int) -> Path:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           return self.stills_path / f"camera_{camera_id}" / f"still_{timestamp}.jpg"

       async def capture_still(self, camera_id: int) -> str | None:
           camera = camera_manager.get_camera(camera_id)
           if not camera:
               logger.error("camera_not_found", camera_id=camera_id)
               return None

           frame = await camera.capture_frame()
           if not frame:
               logger.error("capture_failed", camera_id=camera_id)
               return None

           filepath = self._generate_filename(camera_id)
           filepath.parent.mkdir(parents=True, exist_ok=True)
           filepath.write_bytes(frame.data)

           logger.info("still_captured", camera_id=camera_id, path=str(filepath))
           return str(filepath)
   ```

2. **Create `app/services/camera/recording.py`**
   ```python
   from pathlib import Path
   from datetime import datetime
   from typing import Optional
   import asyncio
   import subprocess
   import structlog

   from app.services.camera.manager import camera_manager
   from app.services.camera.pipeline import GStreamerPipeline, PipelineConfig

   logger = structlog.get_logger(__name__)

   class RecordingJob:
       def __init__(self, camera_id: int, output_path: Path, pipeline_str: str):
           self.camera_id = camera_id
           self.output_path = output_path
           self.pipeline_str = pipeline_str
           self.process: Optional[subprocess.Popen] = None
           self.started_at: Optional[datetime] = None

       async def start(self) -> bool:
           if not await camera_manager.start_recording(self.camera_id):
               return False

           self.process = subprocess.Popen(
               ["gst-launch-1.0"] + self.pipeline_str.split(),
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
           )
           self.started_at = datetime.now()
           logger.info("recording_started", camera_id=self.camera_id, path=str(self.output_path))
           return True

       async def stop(self) -> None:
           if self.process:
               self.process.terminate()
               try:
                   self.process.wait(timeout=5)
               except subprocess.TimeoutExpired:
                   self.process.kill()
               self.process = None

           await camera_manager.stop_recording(self.camera_id)
           logger.info("recording_stopped", camera_id=self.camera_id)

   class RecordingService:
       def __init__(self, recordings_path: str):
           self.recordings_path = Path(recordings_path)
           self.recordings_path.mkdir(parents=True, exist_ok=True)
           self._active_jobs: dict[int, RecordingJob] = {}

       def _generate_filename(self, camera_id: int) -> Path:
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           return self.recordings_path / f"camera_{camera_id}" / f"recording_{timestamp}.mp4"

       async def start_recording(
           self,
           camera_id: int,
           config: PipelineConfig,
       ) -> str | None:
           if camera_id in self._active_jobs:
               return None

           output_path = self._generate_filename(camera_id)
           output_path.parent.mkdir(parents=True, exist_ok=True)

           pipeline = GStreamerPipeline.recording_pipeline(config, str(output_path))
           job = RecordingJob(camera_id, output_path, pipeline)

           if await job.start():
               self._active_jobs[camera_id] = job
               return str(output_path)
           return None

       async def stop_recording(self, camera_id: int) -> bool:
           job = self._active_jobs.pop(camera_id, None)
           if job:
               await job.stop()
               return True
           return False

       def is_recording(self, camera_id: int) -> bool:
           return camera_id in self._active_jobs
   ```

### Acceptance Criteria
- [ ] Still capture saves JPEG files
- [ ] Recording creates valid MP4 files
- [ ] Files organized by camera
- [ ] Graceful stop on disconnect

---

## Phase 6: API Endpoints

### Goal
Expose camera operations via REST API.

### Tasks

1. **Create `app/api/routes/cameras.py`**
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from fastapi.responses import StreamingResponse
   from sqlalchemy.ext.asyncio import AsyncSession
   from datetime import datetime

   from app.db.session import get_session
   from app.db.repositories.camera import CameraRepository
   from app.models.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
   from app.models.schemas.common import ResponseWrapper, Meta
   from app.services.camera.manager import camera_manager
   from app.services.camera.base import CameraConfig

   router = APIRouter(prefix="/cameras")

   @router.get("", response_model=ResponseWrapper[list[CameraResponse]])
   async def list_cameras(session: AsyncSession = Depends(get_session)):
       repo = CameraRepository(session)
       cameras = await repo.get_all()
       return ResponseWrapper(
           data=[CameraResponse.model_validate(c) for c in cameras],
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.get("/{camera_id}", response_model=ResponseWrapper[CameraResponse])
   async def get_camera(camera_id: int, session: AsyncSession = Depends(get_session)):
       repo = CameraRepository(session)
       camera = await repo.get(camera_id)
       if not camera:
           raise HTTPException(status_code=404, detail="Camera not found")
       return ResponseWrapper(
           data=CameraResponse.model_validate(camera),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.post("", response_model=ResponseWrapper[CameraResponse])
   async def create_camera(
       data: CameraCreate,
       session: AsyncSession = Depends(get_session),
   ):
       from app.models.database import Camera
       repo = CameraRepository(session)
       camera = Camera(**data.model_dump())
       camera = await repo.create(camera)
       return ResponseWrapper(
           data=CameraResponse.model_validate(camera),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.get("/{camera_id}/stream")
   async def stream_camera(camera_id: int, session: AsyncSession = Depends(get_session)):
       repo = CameraRepository(session)
       camera = await repo.get(camera_id)
       if not camera:
           raise HTTPException(status_code=404, detail="Camera not found")

       # Parse resolution
       w, h = map(int, camera.resolution.split("x"))
       config = CameraConfig(
           device_path=camera.device_path,
           resolution=(w, h),
           fps=camera.fps,
       )

       await camera_manager.open_camera(camera_id, config)
       if not await camera_manager.start_stream(camera_id):
           raise HTTPException(status_code=503, detail="Max streams reached")

       async def generate():
           cam = camera_manager.get_camera(camera_id)
           if not cam:
               return
           async for frame in cam.stream_frames():
               yield (
                   b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame.data + b"\r\n"
               )

       return StreamingResponse(
           generate(),
           media_type="multipart/x-mixed-replace; boundary=frame",
       )

   @router.post("/{camera_id}/capture")
   async def capture_still(camera_id: int, session: AsyncSession = Depends(get_session)):
       # Implementation calls CaptureService
       pass

   @router.post("/{camera_id}/record/start")
   async def start_recording(camera_id: int, session: AsyncSession = Depends(get_session)):
       # Implementation calls RecordingService
       pass

   @router.post("/{camera_id}/record/stop")
   async def stop_recording(camera_id: int, session: AsyncSession = Depends(get_session)):
       # Implementation calls RecordingService
       pass
   ```

### Acceptance Criteria
- [ ] All CRUD endpoints work
- [ ] MJPEG stream endpoint functional
- [ ] Capture/record endpoints operational
- [ ] Proper error responses

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| Discovery | Unit | Mock subprocess calls |
| Camera base | Unit | Interface contracts |
| Manager limits | Unit | Concurrent limits |
| API endpoints | Integration | Full request cycle |

---

## Resource Budgets (Pi 3)

| Operation | CPU | RAM | Notes |
|-----------|-----|-----|-------|
| Idle | <5% | 50MB | Manager overhead |
| Preview (1 cam) | 15-20% | 80MB | MJPEG encoding |
| Recording (1 cam) | 40-50% | 100MB | H.264 hardware enc |
| Capture | spike | +20MB | Brief allocation |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/03-camera-system.md`
