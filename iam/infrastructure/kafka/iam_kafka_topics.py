"""IAM bounded context Kafka topic definitions.

Owned by the IAM bounded context; only topics produced or consumed
by this context belong here.
"""

from shared.infrastructure.kafka_topics import KafkaTopicConfig


class IamKafkaTopics:
    """Topics produced or consumed by the IAM bounded context."""

    DEVICE_PRESENCE_CHANGED = KafkaTopicConfig(
        name="clair.device.presence.changed",
        num_partitions=1,
        replication_factor=1,
        retention_ms=259200000,  # 3 days
    )

    @classmethod
    def all(cls) -> list[KafkaTopicConfig]:
        return [
            cls.DEVICE_PRESENCE_CHANGED,
        ]
