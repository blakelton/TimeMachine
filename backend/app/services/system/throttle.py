"""Raspberry Pi throttle detection via vcgencmd."""

import subprocess
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Throttle flag bits from vcgencmd get_throttled
THROTTLE_FLAGS = {
    0: "under_voltage_detected",
    1: "arm_frequency_capped",
    2: "currently_throttled",
    3: "soft_temp_limit_active",
    16: "under_voltage_occurred",
    17: "arm_frequency_capped_occurred",
    18: "throttling_occurred",
    19: "soft_temp_limit_occurred",
}


@dataclass
class ThrottleStatus:
    """Raspberry Pi throttle status."""

    available: bool
    raw_value: str | None = None
    is_throttled: bool = False
    active: list[str] | None = None
    historical: list[str] | None = None
    error: str | None = None


def get_throttle_status() -> ThrottleStatus:
    """Get Pi throttle status from vcgencmd.

    Returns:
        ThrottleStatus with current throttle information.
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return ThrottleStatus(
                available=False,
                error=f"vcgencmd failed: {result.stderr.strip()}",
            )

        # Parse "throttled=0x50005"
        output = result.stdout.strip()
        if "=" not in output:
            return ThrottleStatus(
                available=False,
                error=f"Unexpected output format: {output}",
            )

        hex_value = output.split("=")[1]
        flags = int(hex_value, 16)

        active_flags = []
        historical_flags = []

        for bit, name in THROTTLE_FLAGS.items():
            if flags & (1 << bit):
                if bit < 16:
                    active_flags.append(name)
                else:
                    historical_flags.append(name)

        return ThrottleStatus(
            available=True,
            raw_value=hex_value,
            is_throttled=len(active_flags) > 0,
            active=active_flags if active_flags else None,
            historical=historical_flags if historical_flags else None,
        )

    except FileNotFoundError:
        return ThrottleStatus(
            available=False,
            error="vcgencmd not found (not running on Raspberry Pi?)",
        )
    except subprocess.TimeoutExpired:
        logger.warning("throttle_check_timeout")
        return ThrottleStatus(
            available=False,
            error="vcgencmd timed out",
        )
    except Exception as e:
        logger.warning("throttle_check_failed", error=str(e))
        return ThrottleStatus(
            available=False,
            error=str(e),
        )


def get_cpu_temperature() -> float | None:
    """Get CPU temperature from vcgencmd.

    Returns:
        Temperature in Celsius or None if unavailable.
    """
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        # Parse "temp=45.0'C"
        output = result.stdout.strip()
        temp_str = output.replace("temp=", "").replace("'C", "")
        return float(temp_str)

    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None
