"""KafkaCoreContextFacadeImpl - Kafka implementation of the Core ACL facade.

Publishes integration events to core topics using a shared KafkaProducer.
Keeps the device bounded context decoupled from Kafka internals.
"""

import logging

from device.application.outboundservices.acl.core_context_facade import (
    CoreContextFacade,
)
from device.infrastructure.kafka.device_kafka_topics import DeviceKafkaTopics
from shared.infrastructure.core_edge_http_client import CoreEdgeHttpClient
from shared.infrastructure.kafka_client import KafkaInfrastructureClient

logger = logging.getLogger(__name__)


class KafkaCoreContextFacadeImpl(CoreContextFacade):
    """Kafka-based ACL implementation that posts integration events to the core system."""

    def __init__(self, kafka_client: KafkaInfrastructureClient | None = None) -> None:
        self._kafka_client = kafka_client or KafkaInfrastructureClient()
        self._core_http_client = CoreEdgeHttpClient()
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            self._producer = self._kafka_client.create_producer()
        return self._producer

    def publish_telemetry_recorded(self, payload: dict) -> bool:
        """Publish telemetry to Kafka topic vinevault.device.telemetry.recorded."""
        producer = self._get_producer()
        if producer is None:
            logger.warning("Kafka producer unavailable; trying HTTP telemetry fallback")
            http_payload = self._build_telemetry_http_payload(payload)
            return self._core_http_client.publish_telemetry(http_payload)
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
            http_payload = self._build_telemetry_http_payload(payload)
            if self._core_http_client.publish_telemetry(http_payload):
                logger.info("Telemetry delivered to core over HTTP fallback")
                return True
            return False

    def publish_command_acknowledged(self, payload: dict) -> bool:
        """Publish command ACK to Kafka topic vinevault.device.commands.acknowledged."""
        producer = self._get_producer()
        if producer is None:
            logger.warning("Kafka producer unavailable; trying HTTP command ACK fallback")
            http_payload = self._build_command_ack_http_payload(payload)
            return self._core_http_client.publish_command_ack(http_payload)
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
            http_payload = self._build_command_ack_http_payload(payload)
            if self._core_http_client.publish_command_ack(http_payload):
                logger.info("Command ACK delivered to core over HTTP fallback")
                return True
            return False

    def close(self) -> None:
        """Flush and close the underlying producer."""
        if self._producer:
            self._producer.flush()

    @staticmethod
    def _build_telemetry_http_payload(payload: dict) -> dict:
        """Translate the local telemetry payload to the core HTTP contract."""
        return {
            "device_id": payload.get("device_id"),
            "hardware_id": payload.get("hardware_id"),
            "source": payload.get("source", "edge"),
            "occurred_at": payload.get("occurred_at") or payload.get("recorded_at"),
            "payload": {
                "device_time": payload.get("device_time"),
                "uptime_seconds": payload.get("uptime_seconds"),
                "co2": payload.get("co2"),
                "temperature": payload.get("temperature"),
                "humidity": payload.get("humidity"),
                "wifi_status": payload.get("wifi_status"),
                "network_name": payload.get("network_name"),
                "signal_strength": payload.get("signal_strength"),
                "country": payload.get("country"),
                "health_status": payload.get("health_status"),
                "status": payload.get("status"),
                "recorded_at": payload.get("recorded_at"),
            },
        }

    @staticmethod
    def _build_command_ack_http_payload(payload: dict) -> dict:
        """Translate the local ACK payload to the core HTTP contract."""
        return {
            "device_id": payload.get("device_id"),
            "hardware_id": payload.get("hardware_id"),
            "command_id": payload.get("command_id"),
            "status": payload.get("status"),
            "failure_reason": payload.get("failure_reason"),
            "acknowledged_at": payload.get("acknowledged_at"),
        }
