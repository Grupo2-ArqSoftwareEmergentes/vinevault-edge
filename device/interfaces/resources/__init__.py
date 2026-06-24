"""Device interface resources package."""

from device.interfaces.resources.telemetry_request import (
    AirQualityData,
    ConnectivityData,
    LocationData,
    TelemetryRequest,
)
from device.interfaces.resources.device_command_resource import (
    AcknowledgeDeviceCommandRequest,
    device_command_to_dict,
)

__all__ = [
    "AcknowledgeDeviceCommandRequest",
    "AirQualityData",
    "ConnectivityData",
    "LocationData",
    "TelemetryRequest",
    "device_command_to_dict",
]
