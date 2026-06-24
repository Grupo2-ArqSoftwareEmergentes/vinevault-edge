"""Peewee ORM models for the Alerting bounded context.

Stores alert incident events received from the core system so the embedded device
can pull them from the edge API.
"""

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    Model,
)

from shared.infrastructure.database import db


class AlertIncidentEventModel(Model):
    """Edge-local record of alert incident events emitted by the core system."""

    id = AutoField()

    # Key used by embedded authentication and command pulling.
    hardware_id = CharField(index=True)

    # Values from core integration event.
    alert_id = CharField(index=True)
    device_id = CharField(index=True)
    space_id = CharField(null=True)
    metric = CharField()
    status = CharField(index=True)
    message = CharField(null=True)
    threshold_value = CharField(null=True)
    actual_value = CharField(null=True)
    occurred_at = DateTimeField()
    resolved_at = DateTimeField(null=True)

    received_at = DateTimeField()
    delivered_at = DateTimeField(null=True)
    acknowledged_at = DateTimeField(null=True)

    class Meta:
        database = db
        table_name = "alert_incident_events"
        indexes = (
            (("hardware_id", "delivered_at"), False),
            (("hardware_id", "received_at"), False),
        )
