"""KafkaCoreContextFacadeImpl - Kafka implementation of the Core ACL facade.

Publishes integration events to core topics using a shared KafkaProducer.
Keeps the device bounded context decoupled from Kafka internals.
"""

import logging

from device.application.outboundservices.acl.core_context_facade import (
    CoreContextFacade,
)
from device.infrastructure.kafka.device_kafka_topics import DeviceKafkaTopics
from shared.infrastructure.kafka_client import KafkaInfrastructureClient

logger = logging.getLogger(__name__)


class KafkaCoreContextFacadeImpl(CoreContextFacade):
    """Kafka-based ACL implementation that posts integration events to the core system."""

    def __init__(self, kafka_client: KafkaInfrastructureClient | None = None) -> None:
        self._kafka_client = kafka_client or KafkaInfrastructureClient()
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            self._producer = self._kafka_client.create_producer()
        return self._producer

    def publish_telemetry_recorded(self, payload: dict) -> bool:
        """Publish telemetry to Kafka topic clair.device.telemetry.recorded."""
        producer = self._get_producer()
        if producer is None:
            logger.warning("Kafka producer unavailable; telemetry publish skipped")
            return False
        try:
            hardware_id = payload.get("hardware_id", "unknown")
            producer.send(
                DeviceKafkaTopics.TELEMETRY_RECORDED.name,
                key=hardware_id,
                value=payload,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to publish telemetry to Kafka: %s", exc)
            return False

    def publish_command_acknowledged(self, payload: dict) -> bool:
        """Publish command ACK to Kafka topic clair.device.commands.acknowledged."""
        producer = self._get_producer()
        if producer is None:
            logger.warning("Kafka producer unavailable; command ACK publish skipped")
            return False
        try:
            command_id = payload.get("command_id", "unknown")
            producer.send(
                DeviceKafkaTopics.COMMANDS_ACKNOWLEDGED.name,
                key=command_id,
                value=payload,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to publish command ACK to Kafka: %s", exc)
            return False

    def close(self) -> None:
        """Flush and close the underlying producer."""
        if self._producer:
            self._producer.flush()
