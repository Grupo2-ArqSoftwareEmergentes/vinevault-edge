"""KafkaProvisioningConsumer — background consumer for Core -> Edge device provisioning.

Listens on the configured provisioning topic and updates the local
SQLite device cache in real time. Kafka remains the primary sync path
while the HTTP fallback only runs when the cache stays empty.
"""

import json
import logging
import threading
from typing import Optional

from kafka import KafkaConsumer

from provisioning.application.services.device_provisioning_application_service import DeviceProvisioningApplicationService
from provisioning.infrastructure.kafka.provisioning_kafka_topics import ProvisioningKafkaTopics
from shared.infrastructure.environment import get_kafka_bootstrap_servers
from shared.infrastructure.kafka_topics import KafkaConsumerGroups

logger = logging.getLogger(__name__)


class KafkaProvisioningConsumer:
    """Background consumer that processes device provisioning events from Kafka.

    Ensures the edge cache stays synchronized with the core system without any
    HTTP communication.
    """

    def __init__(self) -> None:
        self.provisioning_service = DeviceProvisioningApplicationService()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._consumer: Optional[KafkaConsumer] = None

    def start(self) -> None:
        """Start the background consumer thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("KafkaProvisioningConsumer started")

    def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                logger.exception("Error closing Kafka consumer")

    def _run(self) -> None:
        """Main loop: subscribe and consume provisioning messages."""
        self._consumer = KafkaConsumer(
            ProvisioningKafkaTopics.DEVICES_CHANGED.name,
            bootstrap_servers=get_kafka_bootstrap_servers(),
            group_id=KafkaConsumerGroups.EDGE_PROVISIONING_CONSUMER,
            auto_offset_reset="earliest",
            # Commit offsets only after the SQLite cache has been updated successfully.
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda m: m.decode("utf-8") if m else None,
        )

        try:
            for message in self._consumer:
                if not self._running:
                    break
                try:
                    logger.info(
                        "Received provisioning message: device_id=%s hardware_id=%s status=%s",
                        message.value.get("device_id") or message.value.get("deviceId") or message.value.get("id"),
                        message.value.get("hardware_id") or message.value.get("hardwareId"),
                        message.value.get("status"),
                    )
                    self._handle_message(message.value)
                    # At-least-once delivery: commit only after successful processing.
                    self._consumer.commit()
                except Exception:
                    logger.exception("Failed to handle provisioning message: %s", message.value)
        except Exception:
            logger.exception("Kafka provisioning consumer loop error")
        finally:
            if self._consumer:
                self._consumer.close()
                self._consumer = None

    def _handle_message(self, payload: dict) -> None:
        """Process a single DeviceChanged integration event."""
        self.provisioning_service.handle_device_changed_event(payload)
        logger.info(
            "Provisioned device %s via Kafka (change_type=%s)",
            payload.get("device_id") or payload.get("hardware_id"),
            payload.get("change_type") or payload.get("changeType") or "UNKNOWN",
        )
