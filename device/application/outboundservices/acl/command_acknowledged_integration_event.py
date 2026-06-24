"""DeviceCommandAcknowledgedIntegrationEvent - outbound ACL DTO for command ACKs.

Published by the Device bounded context to Kafka topic
`clair.device.commands.acknowledged` for consumption by the core system.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceCommandAcknowledgedIntegrationEvent:
    """Event published when the embedded device acknowledges a command."""

    device_id: str
    hardware_id: str
    command_id: str
    status: str  # EXECUTED | FAILED
    failure_reason: Optional[str]
    acknowledged_at: str
