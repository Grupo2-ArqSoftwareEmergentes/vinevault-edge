"""DevicePresenceChangedIntegrationEvent — outbound ACL DTO for presence transitions.

Published by the IAM bounded context to Kafka topic
`vinevault.device.presence.changed` for consumption by the core system.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DevicePresenceChangedIntegrationEvent:
    """Event published when the edge detects an ONLINE/OFFLINE transition."""

    device_id: str
    hardware_id: str
    status: str  # ONLINE | OFFLINE | STANDBY | ERROR
    occurred_at: str
