"""Peewee ORM model for the devices table.

Maps the local core device cache to the SQLite 'devices' table.
"""

from peewee import BooleanField, CharField, DateTimeField, TextField, Model

from shared.infrastructure.database import db


class DeviceModel(Model):
    """Peewee model representing the 'devices' table in SQLite.

    Columns:
        device_id: Primary key — logical device identifier.
        hardware_id: Unique physical hardware ID.
        api_key: Secret authentication key for physical device -> edge communication.
        serial_number: Core serial number.
        name: Device display name.
        factory_name: Factory or site name in the core.
        device_type: Core device type classification.
        assigned: Whether the device has an active assignment.
        space_id: Assigned space identifier.
        owner_user_id: Owner user identifier.
        configuration: JSON configuration payload as text.
        activated_at: Activation timestamp.
        status: Lifecycle state synchronized from the core system.
        created_at: Registration timestamp.
        last_seen_at: Last telemetry timestamp (nullable).
    """

    device_id = CharField(primary_key=True)
    hardware_id = CharField(unique=True)
    api_key = CharField(null=True)
    serial_number = CharField(null=True)
    name = CharField(null=True)
    factory_name = CharField(null=True)
    device_type = CharField(null=True)
    assigned = BooleanField(default=False)
    space_id = CharField(null=True)
    owner_user_id = CharField(null=True)
    configuration = TextField(null=True)
    activated_at = DateTimeField(null=True)
    status = CharField()
    created_at = DateTimeField()
    last_seen_at = DateTimeField(null=True)

    class Meta:
        database = db
        table_name = 'devices'
