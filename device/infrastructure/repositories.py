"""DeviceTelemetry repository — infrastructure layer.

Provides data access operations for the DeviceTelemetry aggregate root,
mapping between Peewee models and domain entities.
"""

from typing import Optional

from datetime import datetime, timezone

from device.domain.entities import (
    DeviceCommand,
    DeviceCommandType,
    DeviceTelemetry,
    EdgeDeviceCommandStatus,
)
from device.domain.valueobjects import AirQuality, Connectivity, Location
from device.infrastructure.models import DeviceCommandModel, DeviceTelemetryModel


class DeviceTelemetryRepository:
    """Repository for DeviceTelemetry aggregate root persistence."""

    def save(self, telemetry: DeviceTelemetry) -> DeviceTelemetry:
        """Persist a telemetry record to the database.

        Args:
            telemetry: A DeviceTelemetry domain entity to persist.

        Returns:
            A new DeviceTelemetry domain entity with the database-assigned ID.
        """
        model = DeviceTelemetryModel.create(
            device_id=telemetry.device_id,
            device_time=telemetry.device_time,
            uptime_seconds=telemetry.uptime_seconds,
            co2=telemetry.air_quality.co2,
            temperature=telemetry.air_quality.temperature,
            humidity=telemetry.air_quality.humidity,
            wifi_status=telemetry.connectivity.status,
            network_name=telemetry.connectivity.network,
            signal_strength=telemetry.connectivity.signal_strength,
            country=telemetry.location.country,
            health_status=telemetry.health_status,
            status=telemetry.status,
            recorded_at=telemetry.recorded_at,
        )

        return self._model_to_entity(model)

    def find_by_id(self, record_id: int) -> Optional[DeviceTelemetry]:
        """Find a telemetry record by its database ID.

        Args:
            record_id: The database ID to search for.

        Returns:
            DeviceTelemetry entity if found, None otherwise.
        """
        try:
            model = DeviceTelemetryModel.get(DeviceTelemetryModel.id == record_id)
            return self._model_to_entity(model)
        except DeviceTelemetryModel.DoesNotExist:
            return None

    def find_last_telemetry_by_hardware_id(self, hardware_id: str) -> Optional[DeviceTelemetry]:
        """Find the most recent telemetry record for a device.

        Args:
            hardware_id: The physical hardware identifier.

        Returns:
            The most recent DeviceTelemetry entity, or None if no records exist.
        """
        try:
            model = (
                DeviceTelemetryModel.select()
                .where(DeviceTelemetryModel.device_id == hardware_id)
                .order_by(DeviceTelemetryModel.recorded_at.desc())
                .limit(1)
                .get()
            )
            return self._model_to_entity(model)
        except DeviceTelemetryModel.DoesNotExist:
            return None

    def _model_to_entity(self, model: DeviceTelemetryModel) -> DeviceTelemetry:
        """Convert a Peewee model instance to a DeviceTelemetry domain entity.

        Args:
            model: A DeviceTelemetryModel instance from the database.

        Returns:
            A fully populated DeviceTelemetry domain entity.
        """
        air_quality = AirQuality(
            co2=model.co2,
            temperature=model.temperature,
            humidity=model.humidity,
        )

        connectivity = Connectivity(
            status=model.wifi_status,
            network=model.network_name,
            signal_strength=model.signal_strength,
        )

        location = Location(
            country=model.country,
        )

        return DeviceTelemetry(
            id=model.id,
            device_id=model.device_id,
            device_time=model.device_time,
            uptime_seconds=model.uptime_seconds,
            air_quality=air_quality,
            connectivity=connectivity,
            location=location,
            health_status=model.health_status,
            status=model.status,
            recorded_at=model.recorded_at,
        )


class DeviceCommandRepository:
    """Repository for edge-local DeviceCommand aggregate persistence."""

    def save(self, command: DeviceCommand) -> DeviceCommand:
        """Insert or update a device command and return the persisted entity."""
        DeviceCommandModel.insert(
            command_id=command.command_id,
            device_id=command.device_id,
            hardware_id=command.hardware_id,
            command_type=command.command_type.value,
            status=command.status.value,
            payload=command.payload,
            received_at=command.received_at,
            delivered_at=command.delivered_at,
            acknowledged_at=command.acknowledged_at,
            failure_reason=command.failure_reason,
        ).on_conflict(
            conflict_target=[DeviceCommandModel.command_id],
            update={
                DeviceCommandModel.status: command.status.value,
                DeviceCommandModel.payload: command.payload,
                DeviceCommandModel.delivered_at: command.delivered_at,
                DeviceCommandModel.acknowledged_at: command.acknowledged_at,
                DeviceCommandModel.failure_reason: command.failure_reason,
            },
        ).execute()
        return self.find_by_command_id(command.command_id)

    def find_by_command_id(self, command_id: str) -> Optional[DeviceCommand]:
        """Find a command by its core system command ID."""
        try:
            model = DeviceCommandModel.get(DeviceCommandModel.command_id == command_id)
            return self._model_to_entity(model)
        except DeviceCommandModel.DoesNotExist:
            return None

    def find_pending_for_hardware_id(self, hardware_id: str) -> list[DeviceCommand]:
        """Find commands not yet acknowledged by the embedded device."""
        query = (
            DeviceCommandModel.select()
            .where(
                (DeviceCommandModel.hardware_id == hardware_id)
                & (DeviceCommandModel.status.in_([
                    EdgeDeviceCommandStatus.RECEIVED.value,
                    EdgeDeviceCommandStatus.DELIVERED_TO_EMBEDDED.value,
                ]))
            )
            .order_by(DeviceCommandModel.received_at.asc())
        )
        return [self._model_to_entity(model) for model in query]

    def mark_commands_delivered(self, commands: list[DeviceCommand]) -> list[DeviceCommand]:
        """Mark a batch of commands as delivered to the embedded device."""
        delivered_at = datetime.now(timezone.utc)
        delivered = []
        for command in commands:
            command.mark_delivered_to_embedded(delivered_at)
            delivered.append(self.save(command))
        return delivered

    def _model_to_entity(self, model: DeviceCommandModel) -> DeviceCommand:
        """Convert a Peewee command model into a domain entity."""
        return DeviceCommand(
            command_id=model.command_id,
            device_id=model.device_id,
            hardware_id=model.hardware_id,
            command_type=DeviceCommandType(model.command_type),
            status=EdgeDeviceCommandStatus(model.status),
            payload=model.payload,
            received_at=model.received_at,
            delivered_at=model.delivered_at,
            acknowledged_at=model.acknowledged_at,
            failure_reason=model.failure_reason,
        )
