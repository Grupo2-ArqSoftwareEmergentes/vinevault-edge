"""Background monitor that triggers HTTP device sync when Kafka yields nothing."""

from __future__ import annotations

import logging
import threading
import time

from provisioning.application.services.core_device_sync_service import CoreDeviceSyncService
from shared.infrastructure.environment import (
    get_edge_core_devices_sync_grace_seconds,
    get_edge_core_devices_sync_retry_seconds,
)

logger = logging.getLogger(__name__)


class DeviceCoreSyncFallbackMonitor:
    """Retry HTTP sync from the core until the local cache is populated."""

    def __init__(self) -> None:
        self.core_sync_service = CoreDeviceSyncService()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("DeviceCoreSyncFallbackMonitor started")

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        if not self.core_sync_service.client.is_configured():
            logger.info(
                "DeviceCoreSyncFallbackMonitor disabled because core fallback credentials are missing"
            )
            return

        grace_seconds = get_edge_core_devices_sync_grace_seconds()
        if grace_seconds > 0:
            time.sleep(grace_seconds)

        while self._running:
            if self.core_sync_service.device_cache_repository.count() > 0:
                logger.info("Core device fallback sync skipped because Kafka already populated the cache")
                return

            synced = self.core_sync_service.sync_if_cache_empty()
            if synced > 0:
                logger.info("Core device fallback sync populated %s devices", synced)
                return

            retry_seconds = get_edge_core_devices_sync_retry_seconds()
            logger.info(
                "Core device fallback sync found no devices; retrying in %s seconds",
                retry_seconds,
            )
            time.sleep(retry_seconds)
