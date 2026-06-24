"""TelemetryRecordedIntegrationEvent - outbound ACL DTO for device telemetry.

Published by the Device bounded context to Kafka topic
`clair.device.telemetry.recorded` for consumption by the core system.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryRecordedIntegrationEvent:
    """Event published when the edge persists a telemetry record."""

    device_id: str
    hardware_id: str
    device_time: str
    uptime_seconds: int
    co2: float
    temperature: float
    humidity: float
    wifi_status: str
    network_name: str
    signal_strength: int
    country: str
    health_status: int
    status: str
    recorded_at: str
    occurred_at: str
