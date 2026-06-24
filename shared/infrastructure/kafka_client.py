"""Shared Kafka infrastructure client.

Encapsulates producer creation, topic bootstrapping via KafkaAdminClient,
and common serialization.  Consumer threads live inside bounded contexts,
but they reuse the bootstrap/connection helpers here.
"""

import json
import logging
import time
from typing import Any

from kafka import KafkaAdminClient, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import KafkaError, NoBrokersAvailable, NodeNotReadyError, TopicAlreadyExistsError

from shared.infrastructure.environment import get_kafka_bootstrap_servers
from shared.infrastructure.kafka_topics import KafkaTopicConfig

logger = logging.getLogger(__name__)


class KafkaInfrastructureClient:
    """ORM-style Kafka client that bootstraps topics from Python definitions.

    Usage:
        client = KafkaInfrastructureClient()
        client.bootstrap_topics()
        producer = client.create_producer()
        producer.send("vinevault.device.telemetry.recorded", value={...})
    """

    BOOTSTRAP_RETRY_COUNT = 10
    BOOTSTRAP_RETRY_DELAY_SECONDS = 2

    def __init__(self) -> None:
        self._bootstrap_servers = get_kafka_bootstrap_servers()
        self._producer: KafkaProducer | None = None

    # ------------------------------------------------------------------
    # Topic administration (schema-as-code)
    # ------------------------------------------------------------------
    def bootstrap_topics(self, topics: list[KafkaTopicConfig]) -> None:
        """Ensure the given topics exist in the Kafka cluster.

        Non-destructive: already-existing topics are silently skipped.

        Args:
            topics: Topic configurations to reconcile, usually collected
                from every bounded context at application startup.
        """
        last_error: Exception | None = None
        for attempt in range(1, self.BOOTSTRAP_RETRY_COUNT + 1):
            admin = None
            try:
                admin = KafkaAdminClient(
                    bootstrap_servers=self._bootstrap_servers,
                    client_id="edge-topic-bootstrapper",
                )
                existing = set(admin.list_topics())
                to_create: list[NewTopic] = []
                for cfg in topics:
                    if cfg.name not in existing:
                        to_create.append(
                            NewTopic(
                                name=cfg.name,
                                **cfg.to_new_topic_kwargs(),
                            )
                        )
                        logger.info("Scheduling topic creation: %s", cfg.name)
                    else:
                        logger.debug("Topic already exists: %s", cfg.name)

                if to_create:
                    try:
                        admin.create_topics(to_create)
                        logger.info("Created %s new topic(s)", len(to_create))
                    except TopicAlreadyExistsError:
                        logger.warning("Race condition: topic created concurrently")
                return
            except (NoBrokersAvailable, NodeNotReadyError, KafkaError) as exc:
                last_error = exc
                logger.warning(
                    "Kafka topic bootstrap attempt %s/%s failed: %s",
                    attempt,
                    self.BOOTSTRAP_RETRY_COUNT,
                    exc,
                )
                if attempt < self.BOOTSTRAP_RETRY_COUNT:
                    time.sleep(self.BOOTSTRAP_RETRY_DELAY_SECONDS)
            finally:
                if admin is not None:
                    admin.close()

        if last_error is not None:
            logger.warning(
                "Kafka topic bootstrap skipped after %s attempts: %s",
                self.BOOTSTRAP_RETRY_COUNT,
                last_error,
            )

    # ------------------------------------------------------------------
    # Producer
    # ------------------------------------------------------------------
    def create_producer(self) -> KafkaProducer | None:
        """Return a shared KafkaProducer instance with JSON serialization."""
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self._bootstrap_servers,
                    client_id="edge-service-producer",
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks="all",
                    retries=3,
                    retry_backoff_ms=1000,
                )
                logger.info("KafkaProducer created for %s", self._bootstrap_servers)
            except NoBrokersAvailable:
                logger.warning(
                    "Kafka broker unavailable at %s; producer disabled for now",
                    self._bootstrap_servers,
                )
                return None
        return self._producer

    def close(self) -> None:
        if self._producer:
            self._producer.close()
            self._producer = None
            logger.info("KafkaProducer closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def encode_json(value: Any) -> bytes:
        """Serialize a dict/list to JSON bytes."""
        return json.dumps(value, default=str).encode("utf-8")

    @staticmethod
    def decode_json(data: bytes | None) -> Any:
        """Deserialize JSON bytes to a Python object."""
        if data is None:
            return None
        return json.loads(data.decode("utf-8"))
