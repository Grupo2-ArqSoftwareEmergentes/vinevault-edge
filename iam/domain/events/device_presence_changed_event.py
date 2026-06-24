"""DevicePresenceChangedEvent — domain event for device presence transitions."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DevicePresenceChangedEvent:
    """Event emitted when the edge detects a device presence status change."""

    device_id: str
    hardware_id: str
    status: str
    occurred_at: datetime

    def __post_init__(self):
        if not self.device_id:
            raise ValueError("device_id is required")
        if not self.hardware_id:
            raise ValueError("hardware_id is required")
        if self.status not in ("ONLINE", "OFFLINE", "STANDBY", "ERROR"):
            raise ValueError("status must be ONLINE, OFFLINE, STANDBY, or ERROR")
        if self.occurred_at is None:
            raise ValueError("occurred_at is required")
