import sqlite3
from datetime import datetime


def create_test_device():
    conn = sqlite3.connect("vinevault_edge.db")
    cursor = conn.cursor()

    hardware_id = "VINE-A001"
    api_key = "Dw9nIeSIAX-1eXMOtxVdZ-Xgmd1_DnLyXdv2yHcl3xY"

    cursor.execute(
        "SELECT hardware_id FROM devices WHERE hardware_id = ?",
        (hardware_id,),
    )
    exists = cursor.fetchone()

    if exists:
        print(f"El dispositivo {hardware_id} ya existe, actualizando...")
        cursor.execute(
            """
            UPDATE devices
            SET status = ?, last_seen_at = ?, api_key = ?
            WHERE hardware_id = ?
            """,
            ("active", datetime.now().isoformat(), api_key, hardware_id),
        )
    else:
        print(f"Creando nuevo dispositivo {hardware_id}...")
        cursor.execute(
            """
            INSERT INTO devices (
                hardware_id,
                api_key,
                status,
                created_at,
                last_seen_at,
                device_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                hardware_id,
                api_key,
                "active",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                hardware_id,
            ),
        )

    conn.commit()
    conn.close()
    print(f"Dispositivo {hardware_id} listo para usar")


if __name__ == "__main__":
    create_test_device()
