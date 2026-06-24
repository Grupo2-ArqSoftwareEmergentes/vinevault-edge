"""Device domain services.

Contains business rules for telemetry validation, uptime parsing,
and creation of DeviceTelemetry aggregate roots.
"""

from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as dateutil_parser

from device.domain.commands import CreateFullTelemetryRecordCommand
from device.domain.entities import DeviceTelemetry
from device.domain.valueobjects import AirQuality, Connectivity, Location


class DeviceTelemetryService:
    """Domain service for optimized telemetry validation and creation."""

    @staticmethod
    def create_record_from_command(command: CreateFullTelemetryRecordCommand) -> DeviceTelemetry:
        """Validate command data and create a DeviceTelemetry entity.

        Args:
            command: CreateFullTelemetryRecordCommand with device data.

        Returns:
            A validated DeviceTelemetry aggregate root entity.

        Raises:
            ValueError: If any validation fails.
        """
        air_quality = AirQuality.from_dict(command.air_quality)
        connectivity = Connectivity.from_dict(command.connectivity)
        location = Location.from_dict(command.location)
        uptime_seconds = DeviceTelemetryService._parse_uptime(command.uptime)
        recorded_at = DeviceTelemetryService._parse_timestamp(command.created_at)

        return DeviceTelemetry(
            device_id=command.hardware_id,
            device_time=command.device_time,
            uptime_seconds=uptime_seconds,
            air_quality=air_quality,
            connectivity=connectivity,
            location=location,
            health_status=command.health_status,
            status=command.status,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _parse_uptime(uptime: str) -> int:
        """Parse uptime string to total seconds.

        Supports HH:MM:SS format (e.g., "00:00:20") or plain integer strings.

        Args:
            uptime: Uptime string from the device.

        Returns:
            Total uptime in seconds.

        Raises:
            ValueError: If uptime format is invalid.
        """
        if uptime.isdigit():
            return int(uptime)

        parts = uptime.split(":")
        if len(parts) == 3:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            except ValueError as exc:
                raise ValueError(f"Invalid uptime format: {uptime}") from exc

        raise ValueError(f"Invalid uptime format: {uptime}. Expected HH:MM:SS or integer seconds.")

    @staticmethod
    def _parse_timestamp(created_at: Optional[str]) -> datetime:
        """Parse timestamp string to UTC datetime.

        Args:
            created_at: ISO 8601 timestamp string or None.

        Returns:
            UTC datetime.

        Raises:
            ValueError: If timestamp cannot be parsed.
        """
        if created_at is None:
            return datetime.now(timezone.utc)

        try:
            parsed = dateutil_parser.parse(created_at)
            return parsed.astimezone(timezone.utc)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {created_at}") from e
