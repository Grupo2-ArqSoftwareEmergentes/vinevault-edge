"""Repository for updating the local IAM device cache."""

from datetime import datetime, timezone
import json

from iam.infrastructure.models import DeviceModel


class DeviceCacheRepository:
    """Persists vinevault-core device records in the local SQLite cache."""

    def upsert_many(self, devices):
        """Upsert synchronized devices and return the number of cached records."""
        now = datetime.now(timezone.utc)
        count = 0
        for device in devices:
            configuration = device.get("configuration")
            if isinstance(configuration, (dict, list)):
                configuration = json.dumps(configuration, ensure_ascii=True)
            api_key = device.get("api_key")
            DeviceModel.insert(
                device_id=device["device_id"],
                hardware_id=device["hardware_id"],
                api_key=api_key,
                serial_number=device.get("serial_number"),
                name=device.get("name"),
                factory_name=device.get("factory_name"),
                device_type=device.get("device_type"),
                assigned=bool(device.get("assigned", False)),
                space_id=device.get("space_id"),
                owner_user_id=device.get("owner_user_id"),
                configuration=configuration,
                activated_at=device.get("activated_at"),
                status=device["status"],
                created_at=device.get("created_at") or now,
                last_seen_at=device.get("last_seen_at"),
            ).on_conflict(
                conflict_target=[DeviceModel.device_id],
                preserve=[
                    DeviceModel.created_at,
                    DeviceModel.last_seen_at,
                ],
                update={
                    DeviceModel.hardware_id: device["hardware_id"],
                    DeviceModel.api_key: api_key if api_key else DeviceModel.api_key,
                    DeviceModel.serial_number: device.get("serial_number"),
                    DeviceModel.name: device.get("name"),
                    DeviceModel.factory_name: device.get("factory_name"),
                    DeviceModel.device_type: device.get("device_type"),
                    DeviceModel.assigned: bool(device.get("assigned", False)),
                    DeviceModel.space_id: device.get("space_id"),
                    DeviceModel.owner_user_id: device.get("owner_user_id"),
                    DeviceModel.configuration: configuration,
                    DeviceModel.activated_at: device.get("activated_at"),
                    DeviceModel.status: device["status"],
                },
            ).execute()
            count += 1
        return count

    def count(self) -> int:
        """Return the number of cached devices."""
        return DeviceModel.select().count()
