"""SQLite database configuration and initialization.

Provides the shared SqliteDatabase instance and init_db() function
that creates all tables across bounded contexts.
"""

from peewee import SqliteDatabase

from shared.infrastructure.environment import get_edge_database_path

db = SqliteDatabase(get_edge_database_path())


def _migrate_remove_device_secret():
    """Remove the legacy device_secret column from the devices table.

    Renamed to api_key; this migration cleans up the old column.
    If the database engine does not support DROP COLUMN, the entire
    table is dropped and recreated (data will be re-synced from Kafka).
    """
    from peewee import OperationalError

    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='devices'"
    )
    if not cursor.fetchone():
        return

    col_cursor = db.execute_sql("PRAGMA table_info(devices)")
    columns = {row[1] for row in col_cursor.fetchall()}

    if "device_secret" not in columns:
        return  # Already clean

    try:
        db.execute_sql("ALTER TABLE devices DROP COLUMN device_secret")
    except OperationalError:
        # SQLite < 3.35.0 does not support DROP COLUMN.
        # Drop the whole table; data will be re-synced from Kafka.
        db.execute_sql("DROP TABLE IF EXISTS devices")


def _migrate_telemetry_schema():
    """Recreate device_telemetry table if it still uses the legacy full schema.

    The optimized payload no longer sends deviceHealth, deviceInfo, particulate
    matter, or detailed connectivity fields. If legacy columns are detected,
    the table is dropped so Peewee can create the clean new schema on startup.
    Also recreates if new required columns (signal_strength, health_status) are missing.
    """
    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='device_telemetry'"
    )
    if not cursor.fetchone():
        return

    # Detect legacy column that does not exist in the optimized schema
    col_cursor = db.execute_sql("PRAGMA table_info(device_telemetry)")
    columns = {row[1] for row in col_cursor.fetchall()}
    
    # Drop if legacy columns exist
    if "wifi_ssid" in columns or "free_heap" in columns or "chip_model" in columns:
        db.execute_sql("DROP TABLE IF EXISTS device_telemetry")
        return
    
    # Drop if removed columns still exist
    if "air_quality_valid" in columns or "pm_valid" in columns:
        db.execute_sql("DROP TABLE IF EXISTS device_telemetry")
        return

    # Drop if legacy particulate matter columns still exist
    if "pm1_0" in columns or "pm2_5" in columns or "pm10" in columns:
        db.execute_sql("DROP TABLE IF EXISTS device_telemetry")
        return
    
    # Drop if new required columns are missing
    if "signal_strength" not in columns or "health_status" not in columns:
        db.execute_sql("DROP TABLE IF EXISTS device_telemetry")


def _migrate_outbox_schema():
    """Recreate device_outbox if it still stores duplicated JSON payloads."""
    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='device_outbox'"
    )
    if not cursor.fetchone():
        return

    col_cursor = db.execute_sql("PRAGMA table_info(device_outbox)")
    columns = {row[1] for row in col_cursor.fetchall()}
    if "payload" in columns or "api_key" in columns or "device_id" in columns:
        db.execute_sql("DROP TABLE IF EXISTS device_outbox")


def init_db():
    """Initialize the database by creating all tables if they don't exist.

    Uses deferred imports to avoid circular dependencies between
    bounded context modules.
    """
    db.connect()
    try:
        # Deferred imports to avoid circular dependencies
        from iam.infrastructure.models import DeviceModel
        from device.infrastructure.models import DeviceCommandModel, DeviceTelemetryModel
        from device.infrastructure.outbox.outbox_record_model import OutboxRecordModel
        from alerting.infrastructure.models import AlertIncidentEventModel

        _migrate_remove_device_secret()
        _migrate_telemetry_schema()
        _migrate_outbox_schema()
        db.create_tables(
            [
                DeviceModel,
                DeviceTelemetryModel,
                DeviceCommandModel,
                OutboxRecordModel,
                AlertIncidentEventModel,
            ],
            safe=True,
        )
    finally:
        db.close()
