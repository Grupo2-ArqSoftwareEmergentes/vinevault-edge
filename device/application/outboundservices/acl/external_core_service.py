"""ExternalCoreService - consumer-side ACL service for core integration via Kafka.

Translates domain results into integration event payloads and delegates
publishing to the Kafka-based CoreContextFacade, keeping the device bounded
context decoupled from messaging concerns.
"""

from device.application.outboundservices.acl.core_context_facade import (
    CoreContextFacade,
)
from device.application.outboundservices.acl.kafka_core_context_facade import (
    KafkaCoreContextFacadeImpl,
)


class ExternalCoreService:
    """ACL service that forwards device-related integration events to the core system."""

    def __init__(self, facade: CoreContextFacade | None = None) -> None:
        self._facade = facade or KafkaCoreContextFacadeImpl()

    def publish_telemetry_recorded(self, payload: dict) -> bool:
        """Publish a telemetry recorded event to the core system.

        Args:
            payload: The outbound telemetry payload dict.

        Returns:
            True if Kafka accepted the record, False otherwise.
        """
        return self._facade.publish_telemetry_recorded(payload)

    def publish_command_acknowledged(self, payload: dict) -> bool:
        """Publish a command acknowledgement event to the core system.

        Args:
            payload: Dict with device_id, command_id, status, failure_reason.

        Returns:
            True if Kafka accepted the record, False otherwise.
        """
        return self._facade.publish_command_acknowledged(payload)
