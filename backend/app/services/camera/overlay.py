"""Environment data overlay service for timelapse frames.

Stamps environmental sensor data (temperature, humidity, pressure) onto
captured images with optional mini-graph showing recent trends.
"""

import asyncio
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.services.environment.polling import EnvironmentPollingService
    from app.services.environment.sensors import SensorReading

logger = get_logger(__name__)

# Overlay configuration
OVERLAY_PADDING = 10  # Pixels from edge
OVERLAY_BG_COLOR = (0, 0, 0, 180)  # Semi-transparent black
OVERLAY_TEXT_COLOR = (255, 255, 255, 255)  # White
OVERLAY_GRAPH_BG = (40, 40, 40, 200)  # Dark gray background for graph

# Measurement-specific colors (RGBA)
TEMP_COLOR = (255, 80, 80, 255)  # Red for temperature
HUMIDITY_COLOR = (80, 160, 255, 255)  # Blue for humidity
PRESSURE_COLOR = (255, 255, 255, 255)  # White for pressure

# Graph settings
INLINE_GRAPH_WIDTH = 60  # Smaller inline graphs
INLINE_GRAPH_HEIGHT = 16  # Height to fit on same row as text
GRAPH_CACHE_FRAMES = 10  # Regenerate graph every N frames
GRAPH_HISTORY_MINUTES = 30  # Keep 30 minutes of readings

# Font settings - use default PIL font (always available)
FONT_SIZE_LARGE = 16
FONT_SIZE_SMALL = 12


class EnvironmentOverlayService:
    """Service for overlaying environmental data onto timelapse frames."""

    def __init__(
        self,
        device_id: int,
        position: str = "br",
        show_graph: bool = False,
        device_type: str | None = None,
        temperature_unit: str = "C",
    ):
        """Initialize the overlay service.

        Args:
            device_id: Environment device ID to get readings from.
            position: Overlay position - tl, tr, bl, br (default: br).
            show_graph: Whether to show mini temperature graph.
            device_type: Sensor type (dht22, bme280, ds18b20, etc.) for display.
            temperature_unit: Temperature unit (C or F).
        """
        self.device_id = device_id
        self.position = position
        self.show_graph = show_graph
        self.device_type = device_type
        self.temperature_unit = temperature_unit

        # Graph caches (one per measurement type)
        self._temp_graph: Image.Image | None = None
        self._humidity_graph: Image.Image | None = None
        self._graph_cache_frame: int = -GRAPH_CACHE_FRAMES  # Force initial render

        # Reading history for graphs (timestamp, value)
        max_readings = (GRAPH_HISTORY_MINUTES * 60) // 5 + 10  # ~370 readings at 5s interval
        self._temp_history: deque[tuple[datetime, float]] = deque(maxlen=max_readings)
        self._humidity_history: deque[tuple[datetime, float]] = deque(maxlen=max_readings)

        # Try to load a better font, fall back to default
        self._font_large = ImageFont.load_default()
        self._font_small = ImageFont.load_default()

        try:
            # Try to load DejaVu Sans which is commonly available on Linux
            self._font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE_LARGE
            )
            self._font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE_SMALL
            )
        except (OSError, IOError):
            logger.debug("overlay_font_fallback", reason="DejaVu font not found")

    async def load_history_from_database(
        self,
        session_factory,
    ) -> int:
        """Pre-populate graph history from database readings.

        This should be called when starting a timelapse to ensure the graph
        has data from the start, rather than showing "..." until readings
        accumulate during the session.

        Args:
            session_factory: Async database session factory.

        Returns:
            Number of readings loaded.
        """
        if not self.show_graph:
            return 0

        try:
            from app.db.repositories.environment_reading import EnvironmentReadingRepository

            async with session_factory() as session:
                repo = EnvironmentReadingRepository(session)
                readings = await repo.get_recent(
                    device_id=self.device_id,
                    minutes=GRAPH_HISTORY_MINUTES,
                )

                # Add readings to history (they come in desc order, so reverse)
                temp_count = 0
                humidity_count = 0
                for reading in reversed(readings):
                    if reading.temperature is not None:
                        self._temp_history.append(
                            (reading.timestamp, reading.temperature)
                        )
                        temp_count += 1
                    if reading.humidity is not None:
                        self._humidity_history.append(
                            (reading.timestamp, reading.humidity)
                        )
                        humidity_count += 1

                if readings:
                    logger.info(
                        "overlay_history_loaded",
                        device_id=self.device_id,
                        readings_count=len(readings),
                        temp_history=temp_count,
                        humidity_history=humidity_count,
                    )

                return len(readings)

        except Exception as e:
            logger.warning(
                "overlay_history_load_failed",
                device_id=self.device_id,
                error=str(e),
            )
            return 0

    def _get_supported_readings(self) -> dict[str, bool]:
        """Get which readings this device type supports.

        Returns:
            Dict with temperature, humidity, pressure booleans.
        """
        device_type = (self.device_type or "").lower()

        # Map device types to supported measurements
        supports = {
            "dht11": {"temperature": True, "humidity": True, "pressure": False},
            "dht22": {"temperature": True, "humidity": True, "pressure": False},
            "am2303": {"temperature": True, "humidity": True, "pressure": False},
            "bme280": {"temperature": True, "humidity": True, "pressure": True},
            "ds18b20": {"temperature": True, "humidity": False, "pressure": False},
        }

        return supports.get(device_type, {"temperature": True, "humidity": True, "pressure": True})

    def _format_temperature(self, celsius: float | None) -> str:
        """Format temperature with unit conversion if needed."""
        if celsius is None:
            return "--.-"

        if self.temperature_unit == "F":
            value = celsius * 9 / 5 + 32
            return f"{value:.1f}F"
        return f"{celsius:.1f}C"

    def _render_inline_graph(
        self,
        history: deque[tuple[datetime, float]],
        color: tuple[int, int, int, int],
    ) -> Image.Image | None:
        """Render an inline mini-graph for a measurement.

        Args:
            history: Deque of (timestamp, value) tuples.
            color: RGBA color for the graph line.

        Returns:
            RGBA image of the graph, or None if not enough data.
        """
        if len(history) < 2:
            return None

        # Create graph image with transparency
        graph = Image.new("RGBA", (INLINE_GRAPH_WIDTH, INLINE_GRAPH_HEIGHT), OVERLAY_GRAPH_BG)
        draw = ImageDraw.Draw(graph)

        # Get readings as list for processing
        readings = list(history)
        values = [r[1] for r in readings]

        # Calculate min/max for scaling
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val

        # Add padding to range
        if val_range < 1:
            val_range = 1
            min_val -= 0.5
            max_val += 0.5

        padding = val_range * 0.1
        min_val -= padding
        max_val += padding
        val_range = max_val - min_val

        # Calculate time range
        min_time = readings[0][0].timestamp()
        max_time = readings[-1][0].timestamp()
        time_range = max_time - min_time
        if time_range < 1:
            time_range = 1

        # Graph area (with small margin)
        margin = 2
        graph_w = INLINE_GRAPH_WIDTH - 2 * margin
        graph_h = INLINE_GRAPH_HEIGHT - 2 * margin

        # Build points for the line
        points = []
        for ts, val in readings:
            x = margin + ((ts.timestamp() - min_time) / time_range) * graph_w
            y = margin + graph_h - ((val - min_val) / val_range) * graph_h
            points.append((x, y))

        # Draw the line (RGB only, no alpha for line color)
        if len(points) >= 2:
            draw.line(points, fill=color[:3], width=2)

        return graph

    def _calculate_overlay_size(
        self, reading: "SensorReading", supports: dict[str, bool]
    ) -> tuple[int, int]:
        """Calculate the size of the overlay box.

        Args:
            reading: Current sensor reading.
            supports: What measurements the sensor supports.

        Returns:
            Tuple of (width, height).
        """
        line_height = FONT_SIZE_LARGE + 4
        num_lines = 0

        if supports.get("temperature") and reading.temperature is not None:
            num_lines += 1
        if supports.get("humidity") and reading.humidity is not None:
            num_lines += 1
        if supports.get("pressure") and reading.pressure is not None:
            num_lines += 1

        # Minimum of 1 line
        num_lines = max(num_lines, 1)

        height = 8 + (num_lines * line_height)  # Padding + lines

        # Width needs to accommodate text + inline graph
        # Text ~80px (e.g. "T: 25.5C") + gap + graph
        if self.show_graph:
            width = 90 + 4 + INLINE_GRAPH_WIDTH + 8  # text + gap + graph + padding
        else:
            width = 120

        return width, height

    def _get_overlay_position(
        self, image_width: int, image_height: int, overlay_width: int, overlay_height: int
    ) -> tuple[int, int]:
        """Calculate overlay position based on corner setting.

        Args:
            image_width: Width of the source image.
            image_height: Height of the source image.
            overlay_width: Width of the overlay.
            overlay_height: Height of the overlay.

        Returns:
            Tuple of (x, y) position for overlay top-left corner.
        """
        positions = {
            "tl": (OVERLAY_PADDING, OVERLAY_PADDING),
            "tr": (image_width - overlay_width - OVERLAY_PADDING, OVERLAY_PADDING),
            "bl": (OVERLAY_PADDING, image_height - overlay_height - OVERLAY_PADDING),
            "br": (
                image_width - overlay_width - OVERLAY_PADDING,
                image_height - overlay_height - OVERLAY_PADDING,
            ),
        }

        return positions.get(self.position, positions["br"])

    async def apply_overlay(
        self,
        image_path: Path,
        frame_number: int,
        polling_service: "EnvironmentPollingService",
    ) -> bool:
        """Apply environmental data overlay to an image.

        Args:
            image_path: Path to the image file to modify.
            frame_number: Current frame number (for graph caching).
            polling_service: Service to get current sensor readings from.

        Returns:
            True if overlay was applied successfully.
        """
        try:
            # Get current reading
            reading = polling_service.get_latest_reading(self.device_id)
            if reading is None:
                # Log at INFO on first frame to help diagnose issues
                if frame_number == 0:
                    logger.info(
                        "overlay_no_reading_initial",
                        device_id=self.device_id,
                        frame=frame_number,
                        hint="Sensor may still be initializing or has errors",
                    )
                else:
                    logger.debug(
                        "overlay_no_reading",
                        device_id=self.device_id,
                        frame=frame_number,
                    )
                return False

            # Add to history for graphs
            now = datetime.now()
            if reading.temperature is not None:
                self._temp_history.append((now, reading.temperature))
            if reading.humidity is not None:
                self._humidity_history.append((now, reading.humidity))

            # Get what this sensor supports
            supports = self._get_supported_readings()

            # Maybe regenerate graph caches
            if self.show_graph and (frame_number - self._graph_cache_frame) >= GRAPH_CACHE_FRAMES:
                self._temp_graph = self._render_inline_graph(self._temp_history, TEMP_COLOR)
                self._humidity_graph = self._render_inline_graph(self._humidity_history, HUMIDITY_COLOR)
                self._graph_cache_frame = frame_number

            # Run image processing in thread pool to avoid blocking
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._apply_overlay_sync,
                image_path,
                reading,
                supports,
            )

            # Log success periodically (every 10 frames) to confirm overlay is working
            if frame_number % 10 == 0:
                logger.info(
                    "overlay_applied",
                    device_id=self.device_id,
                    frame=frame_number,
                    show_graph=self.show_graph,
                    temp=reading.temperature,
                )

            return True

        except Exception as e:
            logger.error(
                "overlay_error",
                device_id=self.device_id,
                frame=frame_number,
                error=str(e),
                show_graph=self.show_graph,
            )
            return False

    def _apply_overlay_sync(
        self,
        image_path: Path,
        reading: "SensorReading",
        supports: dict[str, bool],
    ) -> None:
        """Synchronous overlay application (runs in thread pool).

        Args:
            image_path: Path to image file.
            reading: Current sensor reading.
            supports: What measurements the sensor supports.
        """
        # Open image
        with Image.open(image_path) as img:
            # Convert to RGBA for alpha compositing
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Calculate overlay dimensions
            overlay_width, overlay_height = self._calculate_overlay_size(reading, supports)

            # Create overlay image
            overlay = Image.new("RGBA", (overlay_width, overlay_height), OVERLAY_BG_COLOR)
            draw = ImageDraw.Draw(overlay)

            # Draw text lines with inline graphs
            y_offset = 4
            line_height = FONT_SIZE_LARGE + 4
            graph_x = 94  # Position for inline graphs (after text)

            if supports.get("temperature") and reading.temperature is not None:
                temp_str = self._format_temperature(reading.temperature)
                draw.text(
                    (8, y_offset),
                    f"T: {temp_str}",
                    fill=TEMP_COLOR,  # Red for temperature
                    font=self._font_large,
                )
                # Add inline temperature graph
                if self.show_graph and self._temp_graph is not None:
                    # Center graph vertically on the text line
                    graph_y = y_offset + (line_height - INLINE_GRAPH_HEIGHT) // 2
                    overlay.paste(self._temp_graph, (graph_x, graph_y), self._temp_graph)
                y_offset += line_height

            if supports.get("humidity") and reading.humidity is not None:
                draw.text(
                    (8, y_offset),
                    f"H: {reading.humidity:.1f}%",
                    fill=HUMIDITY_COLOR,  # Blue for humidity
                    font=self._font_large,
                )
                # Add inline humidity graph
                if self.show_graph and self._humidity_graph is not None:
                    graph_y = y_offset + (line_height - INLINE_GRAPH_HEIGHT) // 2
                    overlay.paste(self._humidity_graph, (graph_x, graph_y), self._humidity_graph)
                y_offset += line_height

            if supports.get("pressure") and reading.pressure is not None:
                draw.text(
                    (8, y_offset),
                    f"P: {reading.pressure:.0f}hPa",
                    fill=PRESSURE_COLOR,  # White for pressure (no graph)
                    font=self._font_large,
                )
                y_offset += line_height

            # Calculate position and paste overlay
            pos_x, pos_y = self._get_overlay_position(
                img.width, img.height, overlay_width, overlay_height
            )

            # Composite overlay onto image
            img.paste(overlay, (pos_x, pos_y), overlay)

            # Convert back to RGB for JPEG and save
            rgb_img = img.convert("RGB")
            rgb_img.save(image_path, "JPEG", quality=95)
