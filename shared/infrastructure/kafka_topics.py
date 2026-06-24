"""Kafka topic configuration primitive — shared infrastructure.

Only the dataclass definition lives here. Each bounded context owns
its own topic registry.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KafkaTopicConfig:
    """Topic configuration defined as an immutable dataclass."""

    name: str
    num_partitions: int
    replication_factor: int
    retention_ms: int = 604800000  # 7 days default
    cleanup_policy: str = "delete"

    def to_new_topic_kwargs(self) -> dict:
        """Return kwargs compatible with kafka.admin.NewTopic."""
        return {
            "num_partitions": self.num_partitions,
            "replication_factor": self.replication_factor,
            "topic_configs": {
                "retention.ms": str(self.retention_ms),
                "cleanup.policy": self.cleanup_policy,
            },
        }


class KafkaConsumerGroups:
    """Consumer group IDs defined as code."""

    EDGE_COMMAND_CONSUMER = "edge-device-commands-consumer"
    EDGE_PROVISIONING_CONSUMER = "edge-provisioning-consumer"
    EDGE_ALERTING_CONSUMER = "edge-alerting-consumer"
