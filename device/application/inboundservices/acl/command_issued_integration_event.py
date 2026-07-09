"""DeviceCommandIssuedIntegrationEvent - inbound ACL DTO for pending commands.

Consumed by the Device bounded context from Kafka topic
`vinevault.device.commands.pending` published by the core system.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceCommandIssuedIntegrationEvent:
    """Event consumed from Core that represents a pending command for a device."""

    command_id: str
    device_id: str
    hardware_id: str
    command_type: str  # STANDBY | WAKE | RESTART
    payload: Optional[str]
    issued_at: str
