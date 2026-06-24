"""KafkaAlertIncidentConsumer — background consumer for Core -> Edge alert incidents.

Listens on the configured alert incident topic and stores events locally so
embedded devices can pull them from the edge API.
"""

import json
import logging
import threading
from typing import Optional

from kafka import KafkaConsumer

from alerting.application.services.alert_incident_event_application_service import (
    AlertIncidentEventApplicationService,
)
from alerting.infrastructure.kafka.alerting_kafka_topics import AlertingKafkaTopics
from shared.infrastructure.environment import get_kafka_bootstrap_servers
from shared.infrastructure.kafka_topics import KafkaConsumerGroups

logger = logging.getLogger(__name__)


class KafkaAlertIncidentConsumer:
    """Background consumer that processes alert incident events from Kafka."""

    def __init__(self) -> None:
        self.alerting_service = AlertIncidentEventApplicationService()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._consumer: Optional[KafkaConsumer] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("KafkaAlertIncidentConsumer started")

    def stop(self) -> None:
        self._running = False
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                logger.exception("Error closing Kafka consumer")

    def _run(self) -> None:
        self._consumer = KafkaConsumer(
            AlertingKafkaTopics.ALERT_INCIDENT_CHANGED.name,
            bootstrap_servers=get_kafka_bootstrap_servers(),
            group_id=KafkaConsumerGroups.EDGE_ALERTING_CONSUMER,
            auto_offset_reset="earliest",
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
                    self._consumer.commit()
                except Exception:
                    logger.exception("Failed to handle alert incident message")
        except Exception:
            logger.exception("Kafka alert incident consumer loop error")
        finally:
            if self._consumer:
                self._consumer.close()
                self._consumer = None

    def _handle_message(self, payload: dict) -> None:
        result = self.alerting_service.ingest_alert_incident_changed_event(payload)
        logger.info(
            "Stored alert incident event (stored=%s, event_id=%s, hardware_id=%s, status=%s)",
            result.stored,
            result.event_id,
            payload.get("hardware_id") or payload.get("hardwareId"),
            payload.get("status"),
        )
