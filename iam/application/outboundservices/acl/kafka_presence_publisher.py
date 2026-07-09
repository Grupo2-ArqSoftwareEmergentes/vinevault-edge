"""KafkaPresencePublisher — ACL for publishing IAM presence events to Kafka.

Encapsulates the Kafka producer details for the IAM bounded context,
keeping domain and application layers decoupled from messaging infrastructure.
"""

import logging

from shared.infrastructure.core_edge_http_client import CoreEdgeHttpClient
from iam.infrastructure.kafka.iam_kafka_topics import IamKafkaTopics
from shared.infrastructure.kafka_client import KafkaInfrastructureClient

logger = logging.getLogger(__name__)


class KafkaPresencePublisher:
    """Publishes DevicePresenceChanged integration events to Kafka."""

    def __init__(self, kafka_client: KafkaInfrastructureClient | None = None) -> None:
        self._kafka_client = kafka_client or KafkaInfrastructureClient()
        self._core_http_client = CoreEdgeHttpClient()
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            self._producer = self._kafka_client.create_producer()
        return self._producer

    def publish_device_presence_changed(self, payload: dict) -> bool:
        """Publish a presence change event to the configured presence topic.

        Args:
            payload: Dict with device_id, hardware_id, status, occurred_at.

        Returns:
            True if Kafka accepted the record, False otherwise.
        """
        producer = self._get_producer()
        if producer is None:
            logger.warning("Kafka producer unavailable; trying HTTP presence fallback")
            http_payload = {
                "device_id": payload.get("device_id"),
                "hardware_id": payload.get("hardware_id"),
                "status": payload.get("status"),
                "occurred_at": payload.get("occurred_at"),
            }
            return self._core_http_client.publish_presence(http_payload)

        try:
            hardware_id = payload.get("hardware_id", "unknown")
            producer.send(
                IamKafkaTopics.DEVICE_PRESENCE_CHANGED.name,
                key=hardware_id,
                value=payload,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to publish presence event to Kafka: %s", exc)
            http_payload = self._build_http_payload(payload)
            if self._core_http_client.publish_presence(http_payload):
                logger.info("Presence event delivered to core over HTTP fallback")
                return True
            return False

    def close(self) -> None:
        if self._producer:
            self._producer.flush()

    @staticmethod
    def _build_http_payload(payload: dict) -> dict:
        return {
            "device_id": payload.get("device_id"),
            "hardware_id": payload.get("hardware_id"),
            "status": payload.get("status"),
            "occurred_at": payload.get("occurred_at"),
        }
