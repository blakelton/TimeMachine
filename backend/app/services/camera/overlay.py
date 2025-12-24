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
OVERLAY_GRAPH_COLOR = (0, 200, 100)  # Green for temperature line
OVERLAY_GRAPH_BG = (40, 40, 40, 200)  # Dark gray background for graph

# Graph settings
GRAPH_WIDTH = 100
GRAPH_HEIGHT = 40
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

        # Graph cache
        self._graph_image: Image.Image | None = None
        self._graph_cache_frame: int = -GRAPH_CACHE_FRAMES  # Force initial render

        # Reading history for graph (timestamp, temperature)
        max_readings = (GRAPH_HISTORY_MINUTES * 60) // 5 + 10  # ~370 readings at 5s interval
        self._readings_history: deque[tuple[datetime, float]] = deque(maxlen=max_readings)

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

    def _render_graph(self) -> Image.Image:
        """Render temperature graph using pure PIL.

        Returns:
            RGBA image of the graph.
        """
        # Create graph image with transparency
        graph = Image.new("RGBA", (GRAPH_WIDTH, GRAPH_HEIGHT), OVERLAY_GRAPH_BG)
        draw = ImageDraw.Draw(graph)

        if len(self._readings_history) < 2:
            # Not enough data - draw "No data" text
            draw.text(
                (GRAPH_WIDTH // 2, GRAPH_HEIGHT // 2),
                "...",
                fill=OVERLAY_TEXT_COLOR,
                font=self._font_small,
                anchor="mm",
            )
            return graph

        # Get readings as list for processing
        readings = list(self._readings_history)
        temps = [r[1] for r in readings]

        # Calculate min/max for scaling
        min_temp = min(temps)
        max_temp = max(temps)
        temp_range = max_temp - min_temp

        # Add padding to range
        if temp_range < 1:
            temp_range = 1
            min_temp -= 0.5
            max_temp += 0.5

        padding = temp_range * 0.1
        min_temp -= padding
        max_temp += padding
        temp_range = max_temp - min_temp

        # Calculate time range
        min_time = readings[0][0].timestamp()
        max_time = readings[-1][0].timestamp()
        time_range = max_time - min_time
        if time_range < 1:
            time_range = 1

        # Graph area (with small margin)
        margin = 2
        graph_w = GRAPH_WIDTH - 2 * margin
        graph_h = GRAPH_HEIGHT - 2 * margin

        # Build points for the line
        points = []
        for ts, temp in readings:
            x = margin + ((ts.timestamp() - min_time) / time_range) * graph_w
            y = margin + graph_h - ((temp - min_temp) / temp_range) * graph_h
            points.append((x, y))

        # Draw the line
        if len(points) >= 2:
            draw.line(points, fill=OVERLAY_GRAPH_COLOR, width=2)

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

        if self.show_graph:
            height += GRAPH_HEIGHT + 4  # Graph + spacing

        width = max(120, GRAPH_WIDTH + 16) if self.show_graph else 120

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
                logger.debug(
                    "overlay_no_reading",
                    device_id=self.device_id,
                    frame=frame_number,
                )
                return False

            # Add to history for graph (only if we have temperature)
            if reading.temperature is not None:
                self._readings_history.append((datetime.now(), reading.temperature))

            # Get what this sensor supports
            supports = self._get_supported_readings()

            # Maybe regenerate graph cache
            if self.show_graph and (frame_number - self._graph_cache_frame) >= GRAPH_CACHE_FRAMES:
                self._graph_image = self._render_graph()
                self._graph_cache_frame = frame_number

            # Run image processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._apply_overlay_sync,
                image_path,
                reading,
                supports,
            )

            return True

        except Exception as e:
            logger.error(
                "overlay_error",
                device_id=self.device_id,
                frame=frame_number,
                error=str(e),
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

            # Draw text lines
            y_offset = 4
            line_height = FONT_SIZE_LARGE + 4

            if supports.get("temperature") and reading.temperature is not None:
                temp_str = self._format_temperature(reading.temperature)
                draw.text(
                    (8, y_offset),
                    f"T: {temp_str}",
                    fill=OVERLAY_TEXT_COLOR,
                    font=self._font_large,
                )
                y_offset += line_height

            if supports.get("humidity") and reading.humidity is not None:
                draw.text(
                    (8, y_offset),
                    f"H: {reading.humidity:.1f}%",
                    fill=OVERLAY_TEXT_COLOR,
                    font=self._font_large,
                )
                y_offset += line_height

            if supports.get("pressure") and reading.pressure is not None:
                draw.text(
                    (8, y_offset),
                    f"P: {reading.pressure:.0f}hPa",
                    fill=OVERLAY_TEXT_COLOR,
                    font=self._font_large,
                )
                y_offset += line_height

            # Add graph if enabled
            if self.show_graph and self._graph_image is not None:
                graph_x = (overlay_width - GRAPH_WIDTH) // 2
                graph_y = y_offset + 2
                overlay.paste(self._graph_image, (graph_x, graph_y))

            # Calculate position and paste overlay
            pos_x, pos_y = self._get_overlay_position(
                img.width, img.height, overlay_width, overlay_height
            )

            # Composite overlay onto image
            img.paste(overlay, (pos_x, pos_y), overlay)

            # Convert back to RGB for JPEG and save
            rgb_img = img.convert("RGB")
            rgb_img.save(image_path, "JPEG", quality=95)
