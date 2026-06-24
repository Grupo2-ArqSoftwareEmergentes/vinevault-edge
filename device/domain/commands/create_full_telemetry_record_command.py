"""CreateFullTelemetryRecordCommand — command to create an optimized telemetry record.

Immutable command representing the intention to persist the lightweight
telemetry reading sent by the embedded device.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateFullTelemetryRecordCommand:
    """Command to create an optimized device telemetry record.

    Attributes:
        hardware_id: Physical hardware identifier from X-Hardware-Id header.
        device_time: Device local time string (e.g., "14:30:25").
        uptime: System uptime as string (e.g., "00:00:20").
        air_quality: Dict with co2, temperature, humidity.
        connectivity: Dict with status, network, signalStrength.
        location: Dict with country.
        health_status: Device health status percentage (0-100).
        status: Overall device status string.
        created_at: Optional timestamp override.
    """
    hardware_id: str
    device_time: str
    uptime: str
    air_quality: dict
    connectivity: dict
    location: dict
    health_status: int
    status: str
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.hardware_id:
            raise ValueError("hardware_id is required")
        if not self.device_time:
            raise ValueError("device_time is required")
        if not self.uptime:
            raise ValueError("uptime is required")
        if not isinstance(self.air_quality, dict):
            raise ValueError("air_quality must be a dict")
        if not isinstance(self.connectivity, dict):
            raise ValueError("connectivity must be a dict")
        if not isinstance(self.location, dict):
            raise ValueError("location must be a dict")
        if self.health_status is None:
            raise ValueError("health_status is required")
        if not self.status:
            raise ValueError("status is required")
