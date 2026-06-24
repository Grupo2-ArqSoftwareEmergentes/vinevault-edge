"""GetDeviceConnectionStatusQuery — query to determine device online/offline status.

Immutable query representing the intention to check if a device is currently
connected based on the time since its last telemetry was received.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetDeviceConnectionStatusQuery:
    """Query to get the connection status of a device.

    Attributes:
        hardware_id: Physical hardware identifier of the device to check.
    """
    hardware_id: str

    def __post_init__(self):
        if not self.hardware_id:
            raise ValueError("hardware_id is required")
