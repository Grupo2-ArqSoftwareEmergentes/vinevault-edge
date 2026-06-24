"""Repository for updating the local IAM device cache."""

from datetime import datetime, timezone

from iam.infrastructure.models import DeviceModel


class DeviceCacheRepository:
    """Persists vinevault-core device records in the local SQLite cache."""

    def upsert_many(self, devices):
        """Upsert synchronized devices and return the number of cached records."""
        now = datetime.now(timezone.utc)
        count = 0
        for device in devices:
            DeviceModel.insert(
                device_id=device["device_id"],
                hardware_id=device["hardware_id"],
                api_key=device["api_key"],
                status=device["status"],
                created_at=now,
                last_seen_at=None,
            ).on_conflict(
                conflict_target=[DeviceModel.device_id],
                preserve=[DeviceModel.created_at, DeviceModel.last_seen_at],
                update={
                    DeviceModel.hardware_id: device["hardware_id"],
                    DeviceModel.api_key: device["api_key"],
                    DeviceModel.status: device["status"],
                },
            ).execute()
            count += 1
        return count
