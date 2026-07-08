# Vinevault Edge Service — IoT Telemetry Ingestion

Servicio edge para la ingesta de telemetría ambiental (CO2, temperatura y humedad) desde dispositivos IoT. Valida el estado del dispositivo localmente (cache) y sincroniza telemetría, comandos y presencia con el sistema core via Kafka.

## Stack Tecnológico

| Tecnología | Propósito |
|---|---|
| **Python 3.13** | Lenguaje principal |
| **uv** | Gestor de paquetes y entornos virtuales |
| **Flask** | Framework web para los endpoints REST |
| **Peewee** | ORM ligero para mapear entidades a SQLite |
| **SQLite** | Base de datos embebida local |

## Arquitectura

El proyecto sigue **Domain-Driven Design (DDD)** con dos bounded contexts:

```
edge-service/
├── app.py                         # Punto de entrada Flask
├── iam/                           # Bounded Context: Identity & Access Management
│   ├── domain/
│   │   ├── entities.py            # Entidad Device (aggregate root, 7 atributos)
│   │   └── services.py            # AuthService: valida credenciales + status sincronizado
│   ├── application/
│   │   └── services.py            # AuthApplicationService: orquesta autenticación local
│   ├── infrastructure/
│   │   ├── models.py              # DeviceModel (Peewee) → tabla 'devices'
│   │   └── repositories.py        # DeviceRepository: find/update_last_seen
│   └── interfaces/
│       └── services.py            # Blueprint iam_api + authenticate_request()
├── device/                        # Bounded Context: Device Telemetry
│   ├── domain/
│   │   ├── entities.py            # Entidad DeviceTelemetry (CO2, PM2.5)
│   │   └── services.py            # Validación de rangos (CO2: 0-5000, PM2.5: 0-500)
│   ├── application/
│   │   └── services.py            # DeviceTelemetryAppService: orquesta validación y guardado
│   ├── infrastructure/
│   │   ├── models.py              # DeviceTelemetryModel → tabla 'device_telemetry'
│   │   └── repositories.py        # DeviceTelemetryRepository: persistencia
│   └── interfaces/
│       └── api.py                 # Blueprint device_api + POST /api/v1/device/telemetry
├── provisioning/                  # Bounded Context: Device Provisioning
│   ├── application/               # Kafka consumer + ACL contra el sistema core
│   ├── domain/                    # Commands, queries y validación de cache
│   ├── infrastructure/            # Upsert del cache local de devices
│   └── interfaces/                # Recursos para consumo Kafka
└── shared/                        # Infraestructura compartida
    └── infrastructure/
        └── database.py            # SqliteDatabase(EDGE_DATABASE_PATH || 'vinevault_edge.db') + init_db()
```

## Requisitos Previos

- **Python 3.13+**
- **uv** (gestor de paquetes)

### Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Cómo Ejecutar

```bash
# Entrar al directorio del proyecto
cd edge-service

# Sincronizar dependencias (crea .venv automáticamente)
uv sync

# Ejecutar el servicio
uv run python app.py
```

El servidor arranca en `http://127.0.0.1:5000` con debug mode activado.

## API Endpoints

### `POST /api/v1/device/telemetry`

Crea un nuevo registro de telemetría ambiental para un dispositivo autenticado.

**Headers requeridos:**

```
Content-Type: application/json
X-Hardware-Id: <hardware-id-del-dispositivo>
X-API-Key: <api-key-del-dispositivo>
```

**Body (JSON):**

```json
{
  "co2": 420.5,
  "pm25": 35.2,
  "created_at": "2026-05-16T22:30:00-05:00"
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `co2` | number | Sí | Concentración de CO2 en ppm (rango: 0–5000) |
| `pm25` | number | Sí | Material particulado PM2.5 en µg/m³ (rango: 0–500) |
| `created_at` | string | No | Timestamp ISO 8601; si se omite usa UTC actual |

**Respuestas:**

| Código | Condición | Body |
|---|---|---|
| `201` | Registro creado | `{"id": 1, "hardware_id": "...", "co2": 420.5, "pm25": 35.2, "created_at": "..."}` |
| `400` | Campos faltantes o valores inválidos | `{"error": "..."}` |
| `401` | Credenciales inválidas o dispositivo no autorizado | `{"error": "..."}` |

### Probar con curl

```bash
curl -X POST http://127.0.0.1:5000/api/v1/device/telemetry \
  -H 'Content-Type: application/json' \
  -H 'X-Hardware-Id: VINEVAULT-0001' \
  -H 'X-API-Key: <api-key>' \
  -d '{
    "co2": 420.5,
    "pm25": 35.2,
    "created_at": "2026-05-16T22:30:00-05:00"
  }'
```

## Sincronizacion de Devices

El edge no crea devices de prueba. Recibe los devices maestros desde el sistema core via Kafka (`vinevault.provisioning.devices.changed`) y los cachea en SQLite para validar telemetria localmente.

La sincronizacion es reactiva via Kafka: el core publica cambios y el edge los consume en tiempo real.

Si Kafka no logra poblar la cachÃ© local, el edge activa un fallback HTTP contra `GET /api/v1/edges/devices` usando solo su propia API key de edge:

```bash
Authorization: Bearer <edge-api-key>
```

Ese fallback pagina con `page` y `size` y solo corre mientras la tabla local siga vacÃ­a.

Variables relevantes:

| Variable | Default | Descripción |
|---|---|---|
| `EDGE_DATABASE_PATH` | `vinevault_edge.db` | Ruta del SQLite local del edge |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Broker Kafka para comunicacion edge <-> core |
| `EDGE_PUBLIC_BASE_URL` | `http://127.0.0.1:5000` | Base URL para el OpenAPI `servers` (docs) |
| `CORE_BASE_URL` | `http://localhost:8000` | Base URL del core para el fallback HTTP |
| `EDGE_CORE_API_KEY` | _(vacÃ­o)_ | API key del edge para autenticarse contra el core |
| `EDGE_CORE_DEVICES_PAGE_SIZE` | `50` | TamaÃ±o de pÃ¡gina para el fallback HTTP, mÃ¡ximo `500` |
| `EDGE_CORE_DEVICES_SYNC_GRACE_SECONDS` | `15` | Espera antes de activar el fallback si la cachÃ© sigue vacÃ­a |
| `EDGE_CORE_DEVICES_SYNC_RETRY_SECONDS` | `30` | Intervalo de reintento mientras la cachÃ© siga vacÃ­a |

Este proyecto soporta archivo `.env` (cargado al iniciar via `python-dotenv`). Usa `.env.example` como base.

## Inspeccionar la Base de Datos

```bash
sqlite3 vinevault_edge.db ".tables"
sqlite3 vinevault_edge.db "SELECT * FROM devices;"
sqlite3 vinevault_edge.db "SELECT * FROM device_telemetry;"
```
