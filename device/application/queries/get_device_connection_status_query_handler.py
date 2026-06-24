"""GetDeviceConnectionStatusQueryHandler — application service for checking device status.

Handles the query to determine if a device is online or offline based on
the time elapsed since its last telemetry reception.
"""

from datetime import datetime, timezone

from device.domain.queries.get_device_connection_status_query import (
    GetDeviceConnectionStatusQuery,
)
from device.domain.valueobjects.device_connection_status import DeviceConnectionStatus
from device.infrastructure.repositories import DeviceTelemetryRepository


class GetDeviceConnectionStatusQueryHandler:
    """Query handler that determines device connection status.

    A device is considered ONLINE if it sent telemetry within the last
    30 seconds. Otherwise, it is considered OFFLINE.
    """

    OFFLINE_THRESHOLD_SECONDS = 30

    def __init__(self, telemetry_repository: DeviceTelemetryRepository = None):
        self.telemetry_repository = telemetry_repository or DeviceTelemetryRepository()

    def handle(self, query: GetDeviceConnectionStatusQuery) -> DeviceConnectionStatus:
        """Execute the query and return the device connection status.

        Args:
            query: GetDeviceConnectionStatusQuery with the hardware_id.

        Returns:
            DeviceConnectionStatus with the calculated status.
        """
        # Find the most recent telemetry record for this device
        last_telemetry = self.telemetry_repository.find_last_telemetry_by_hardware_id(
            query.hardware_id
        )

        if last_telemetry is None:
            return DeviceConnectionStatus(
                hardware_id=query.hardware_id,
                status="OFFLINE",
                last_seen_at=None,
                seconds_since_last_seen=-1,
            )

        last_seen = last_telemetry.recorded_at
        now = datetime.now(timezone.utc)

        # Ensure last_seen is timezone-aware
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        seconds_since = int((now - last_seen).total_seconds())

        status = "ONLINE" if seconds_since < self.OFFLINE_THRESHOLD_SECONDS else "OFFLINE"

        return DeviceConnectionStatus(
            hardware_id=query.hardware_id,
            status=status,
            last_seen_at=last_seen,
            seconds_since_last_seen=seconds_since,
        )
