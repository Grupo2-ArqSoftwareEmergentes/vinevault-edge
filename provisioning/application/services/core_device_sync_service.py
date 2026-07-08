"""HTTP fallback sync for devices when Kafka has not populated the cache."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib import error

from dateutil import parser as date_parser

from provisioning.domain.services.device_cache_service import DeviceCacheService
from provisioning.infrastructure.core_devices_client import CoreDevicesClient
from provisioning.infrastructure.device_cache_repository import DeviceCacheRepository
from shared.infrastructure.environment import get_edge_core_devices_page_size

logger = logging.getLogger(__name__)


class CoreDeviceSyncService:
    """Synchronize device cache data from the core HTTP endpoint."""

    def __init__(self) -> None:
        self.client = CoreDevicesClient()
        self.device_cache_repository = DeviceCacheRepository()
        self.device_cache_service = DeviceCacheService()
        self.page_size = get_edge_core_devices_page_size()

    def sync_if_cache_empty(self) -> int:
        """Sync only when the local cache is still empty."""
        if self.device_cache_repository.count() > 0:
            return 0
        return self.sync_from_core()

    def sync_from_core(self) -> int:
        """Fetch all pages from the core and upsert them into SQLite."""
        if not self.client.is_configured():
            logger.warning(
                "Core device sync skipped because CORE_BASE_URL or EDGE_CORE_API_KEY is missing"
            )
            return 0

        total = 0
        page = 0

        while True:
            try:
                devices, meta = self.client.fetch_page(page=page, size=self.page_size)
            except error.URLError as exc:
                logger.warning("Core device sync failed on page %s: %s", page, exc)
                break
            except Exception as exc:
                logger.exception("Unexpected error while syncing core devices: %s", exc)
                break

            if not devices:
                break

            records = []
            for payload in devices:
                try:
                    record = self._normalize_payload(payload)
                    self.device_cache_service.validate_device_record(record, require_api_key=False)
                    records.append(record)
                except ValueError as exc:
                    logger.warning("Skipping invalid core device payload: %s", exc)

            if records:
                total += self.device_cache_repository.upsert_many(records)

            if self._should_stop(meta, len(devices), page):
                break
            page += 1

        return total

    def _normalize_payload(self, payload: dict) -> dict:
        """Map the core device payload into the local cache schema."""
        if not isinstance(payload, dict):
            raise ValueError("Invalid core device payload")

        device_id = (
            payload.get("id")
            or payload.get("device_id")
            or payload.get("deviceId")
            or payload.get("serial_number")
            or payload.get("serialNumber")
        )
        hardware_id = payload.get("hardware_id") or payload.get("hardwareId") or payload.get("serial_number")
        api_key = (
            payload.get("api_key")
            or payload.get("apiKey")
            or payload.get("edge_api_key")
            or payload.get("edgeApiKey")
            or payload.get("secret")
        )
        active = payload.get("active")
        status = payload.get("status")
        if not status:
            status = "ONLINE" if self._coerce_bool(active) else "DECOMMISSIONED"
        created_at = self._parse_datetime(
            payload.get("created_at")
            or payload.get("createdAt")
            or payload.get("activated_at")
            or payload.get("activatedAt")
        )
        last_seen_at = self._parse_datetime(payload.get("last_seen_at") or payload.get("lastSeenAt"))
        activated_at = self._parse_datetime(payload.get("activated_at") or payload.get("activatedAt"))

        return {
            "device_id": str(device_id) if device_id is not None else None,
            "hardware_id": str(hardware_id) if hardware_id is not None else None,
            "api_key": api_key,
            "serial_number": payload.get("serial_number") or payload.get("serialNumber"),
            "name": payload.get("name"),
            "factory_name": payload.get("factory_name") or payload.get("factoryName"),
            "device_type": payload.get("device_type") or payload.get("deviceType"),
            "assigned": self._coerce_bool(payload.get("assigned")),
            "space_id": payload.get("space_id") or payload.get("spaceId"),
            "owner_user_id": payload.get("owner_user_id") or payload.get("ownerUserId"),
            "configuration": payload.get("configuration"),
            "activated_at": activated_at,
            "status": status,
            "created_at": created_at or datetime.now(timezone.utc),
            "last_seen_at": last_seen_at,
        }

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            parsed = date_parser.parse(str(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _coerce_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"true", "1", "yes", "y", "on"}
        return False

    @staticmethod
    def _should_stop(meta: dict, item_count: int, page: int) -> bool:
        total_pages = meta.get("totalPages")
        if total_pages is None:
            total_pages = meta.get("total_pages")
        last = meta.get("last")
        if last is None:
            last = meta.get("isLast")

        if isinstance(last, bool) and last:
            return True

        try:
            if total_pages is not None and page + 1 >= int(total_pages):
                return True
        except (TypeError, ValueError):
            pass

        size = meta.get("size")
        try:
            if size is not None and item_count < int(size):
                return True
        except (TypeError, ValueError):
            if item_count < 1:
                return True

        return False
