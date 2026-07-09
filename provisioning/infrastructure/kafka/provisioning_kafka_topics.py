"""Provisioning bounded context Kafka topic definitions.

Owned by the Provisioning bounded context; only topics produced or consumed
by this context belong here.
"""

from shared.infrastructure.kafka_topics import KafkaTopicConfig


class ProvisioningKafkaTopics:
    """Topics produced or consumed by the Provisioning bounded context."""

    DEVICES_CHANGED = KafkaTopicConfig(
        name="vinevault.provisioning.devices.changed",
        num_partitions=1,
        replication_factor=1,
        retention_ms=604800000,
    )

    DEVICES_SYNC_REQUESTED = KafkaTopicConfig(
        name="vinevault.provisioning.devices.sync.requested",
        num_partitions=1,
        replication_factor=1,
        retention_ms=86400000,  # 1 day
    )

    @classmethod
    def all(cls) -> list[KafkaTopicConfig]:
        return [
            cls.DEVICES_CHANGED,
            cls.DEVICES_SYNC_REQUESTED,
        ]
