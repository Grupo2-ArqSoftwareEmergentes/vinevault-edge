"""Connectivity value object — represents WiFi connection status.

Immutable value object containing network connection information.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connectivity:
    """WiFi connectivity status from the device.

    Attributes:
        status: Connection status (connected, disconnected, etc.)
        network: WiFi network name/SSID (e.g., "Wokwi-GUEST")
        signal_strength: WiFi signal strength in dBm (e.g., -65)
    """
    status: str
    network: str = ""
    signal_strength: int = 0

    def __post_init__(self):
        """Validate connectivity data."""
        if not self.status:
            raise ValueError("Status cannot be empty")

    @classmethod
    def from_dict(cls, data: dict) -> "Connectivity":
        """Create Connectivity from dictionary payload."""
        return cls(
            status=str(data.get("status", "unknown")),
            network=str(data.get("network", "")),
            signal_strength=int(data.get("signalStrength", 0)),
        )
