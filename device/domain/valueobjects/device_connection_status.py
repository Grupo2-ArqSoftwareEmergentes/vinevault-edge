"""Device connection status value object."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DeviceConnectionStatus:
    """Connection status of a device.

    Attributes:
        hardware_id: Physical hardware identifier.
        status: Connection status (ONLINE or OFFLINE).
        last_seen_at: UTC timestamp when the device was last seen.
        seconds_since_last_seen: Number of seconds since last telemetry.
    """
    hardware_id: str
    status: str  # "ONLINE" or "OFFLINE"
    last_seen_at: Optional[datetime]
    seconds_since_last_seen: int
