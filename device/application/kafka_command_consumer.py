"""KafkaCommandConsumer - background consumer for Core -> Edge device commands.

Replaces the HTTP polling loop with a persistent Kafka consumer that listens
on `vinevault.device.commands.pending` and caches commands locally for embedded
device delivery.
"""

import json
import logging
import threading
from typing import Optional

from kafka import KafkaConsumer

from device.application.services import DeviceCommandApplicationService
from device.infrastructure.kafka.device_kafka_topics import DeviceKafkaTopics
from shared.infrastructure.environment import get_kafka_bootstrap_servers
from shared.infrastructure.kafka_topics import KafkaConsumerGroups

logger = logging.getLogger(__name__)


class KafkaCommandConsumer:
    """Background consumer that polls Kafka for pending device commands.

    Guarantees eventual delivery by consuming commands from Kafka and
    persisting them into the edge local cache.
    """

    def __init__(self) -> None:
        self.command_application_service = DeviceCommandApplicationService()
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
        logger.info("KafkaCommandConsumer started")

    def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                logger.exception("Error closing Kafka consumer")

    def _run(self) -> None:
        """Main loop: subscribe and consume messages."""
        self._consumer = KafkaConsumer(
            DeviceKafkaTopics.COMMANDS_PENDING.name,
            bootstrap_servers=get_kafka_bootstrap_servers(),
            group_id=KafkaConsumerGroups.EDGE_COMMAND_CONSUMER,
            auto_offset_reset="earliest",
            # Commit offsets only after the local cache has been updated successfully.
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda m: m.decode("utf-8") if m else None,
        )

        try:
            for message in self._consumer:
                if not self._running:
                    break
                try:
                    self._handle_message(message.value)
                    # At-least-once delivery: commit only after successful processing.
                    self._consumer.commit()
                except Exception:
                    logger.exception("Failed to handle command message")
        except Exception:
            logger.exception("Kafka consumer loop error")
        finally:
            if self._consumer:
                self._consumer.close()
                self._consumer = None

    def _handle_message(self, payload: dict) -> None:
        """Validate and persist a command event from Kafka."""
        if not isinstance(payload, dict):
            raise ValueError("Command message must be a dict")
        self.command_application_service.ingest_command_messages([payload])
