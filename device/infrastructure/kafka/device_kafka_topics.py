"""Device bounded context Kafka topic definitions.

Owned by the device bounded context; only topics produced or consumed
by this context belong here.
"""

from shared.infrastructure.kafka_topics import KafkaTopicConfig


class DeviceKafkaTopics:
    """Topics produced or consumed by the Device bounded context."""

    TELEMETRY_RECORDED = KafkaTopicConfig(
        name="vinevault.device.telemetry.recorded",
        num_partitions=3,
        replication_factor=1,
        retention_ms=604800000,
    )

    COMMANDS_ACKNOWLEDGED = KafkaTopicConfig(
        name="vinevault.device.commands.acknowledged",
        num_partitions=1,
        replication_factor=1,
        retention_ms=604800000,
    )

    COMMANDS_PENDING = KafkaTopicConfig(
        name="vinevault.device.commands.pending",
        num_partitions=3,
        replication_factor=1,
        retention_ms=604800000,
    )

    @classmethod
    def all(cls) -> list[KafkaTopicConfig]:
        return [
            cls.TELEMETRY_RECORDED,
            cls.COMMANDS_ACKNOWLEDGED,
            cls.COMMANDS_PENDING,
        ]
