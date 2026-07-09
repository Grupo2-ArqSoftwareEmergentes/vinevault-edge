# Vinevault Edge Roadmap

Este documento define la ruta de implementacion para el `edge` de Vinevault, tomando como base el contrato real que hoy expone `vinevault-core`.

La idea no es repetir el core, sino decir con claridad:

1. Que debe consumir el edge.
2. Que debe publicar el edge.
3. Que debe cachear localmente.
4. En que orden conviene implementarlo.

## 1. Objetivo del edge

El edge debe actuar como el runtime cercano al hardware. Su responsabilidad es:

1. Descubrir y mantener el inventario local de devices.
2. Reportar presencia y estado operativo.
3. Recibir comandos desde el core y confirmar su ejecucion.
4. Enviar telemetry de sensores al core.
5. Responder bien cuando el core o la red no esten disponibles.

## 2. Contrato actual con el core

### Autenticacion

- `Authorization: Bearer <edge_api_key>`
  - Asi se autentica el edge contra los endpoints edge del core.
  - No usar `X-Edge-Token` ni `X-API-Key` salvo que se agregue compatibilidad futura.

### Endpoints que el edge debe consumir

- `GET /api/v1/edges/devices`
  - Sincroniza el inventario que el edge ve como propio.
  - Uso recomendado:
    - Arranque del edge.
    - Re-sincronizacion periodica.
    - Recovery despues de perder conectividad.

- `POST /api/v1/edges/devices/presence`
  - Reporta el estado de cada device.
  - Usa `device_id` o `hardware_id`.
  - Debe poder enviarse con `ONLINE`, `OFFLINE`, `STANDBY` o `ERROR`.

- `POST /api/v1/edges/devices/commands/ack`
  - Confirma estados de comandos enviados por el core.
  - Usa `device_id`, `command_id`, `status` y `failure_reason` cuando aplique.

- `POST /api/v1/edges/devices/telemetry`
  - Envía paquetes de telemetry al core.
  - Usa `device_id` o `hardware_id`, `payload`, `source` y `occurred_at` opcional.

### Topics Kafka que el edge debe consumir o producir

- `vinevault.provisioning.devices.changed`
  - Consumir.
  - Sirve para enterarse de cambios de provisioning, pairing, reset o rename.

- `vinevault.device.commands.pending`
  - Consumir.
  - Sirve para recibir comandos que el core genera para un device.

- `vinevault.device.presence.changed`
  - Producir ya existe en el core.
  - El edge no lo publica directamente.

- `vinevault.device.commands.acknowledged`
  - Producir ya existe en el core.
  - El edge no lo publica directamente.

- `vinevault.device.telemetry.recorded`
  - Producir ya existe en el core.
  - El edge no lo publica directamente.

## 3. Flujos que debe implementar el edge

### 3.1 Boot y discovery

Orden recomendado:

1. Cargar configuracion local.
2. Levantar autentificacion hacia el core.
3. Consumir `GET /api/v1/edges/devices`.
4. Guardar cache local de devices y su mapeo `device_id` <-> `hardware_id`.
5. Levantar workers de presencia, comandos y telemetry.

### 3.2 Inventario local

El edge debe mantener una copia local de:

1. `device_id`
2. `hardware_id`
3. `name`
4. `status`
5. `api_key` si aplica para operaciones internas
6. `space_id` si el flujo del edge necesita agrupar devices

Reglas:

1. El cache local no debe ser la fuente de verdad definitiva.
2. Si el core cambia el inventario, el edge debe reconciliar su cache.
3. Si un device desaparece del inventario, el edge debe dejar de operar sobre el.

### 3.3 Presencia

El edge debe emitir presencia cuando:

1. Arranca.
2. Un device cambia de estado.
3. Un device se desconecta.
4. Un device entra a standby.
5. Un error de hardware lo requiere.

Payload recomendado:

```json
{
  "device_id": "uuid-opcional",
  "hardware_id": "VINE-XXXX",
  "status": "ONLINE",
  "occurred_at": "2026-07-08T12:34:56Z"
}
```

### 3.4 Comandos

El edge debe:

1. Escuchar `vinevault.device.commands.pending`.
2. Resolver a que device pertenece cada comando.
3. Ejecutar el comando en hardware o simulador.
4. Reportar ACK al core con `POST /api/v1/edges/devices/commands/ack`.

Estados a manejar:

1. `SENT`
2. `EXECUTED`
3. `FAILED`

Reglas:

1. `FAILED` debe incluir `failure_reason`.
2. Si el comando no puede mapearse a un device conocido, registrar error local y no intentar ejecutar.
3. Si el core repite un comando, el edge debe manejar idempotencia por `command_id`.

### 3.5 Telemetry

El edge debe publicar telemetry de sensores hacia el core.

Payload base:

```json
{
  "device_id": "uuid-opcional",
  "hardware_id": "VINE-XXXX",
  "source": "edge",
  "occurred_at": "2026-07-08T12:34:56Z",
  "payload": {
    "temperature_c": 14.2,
    "humidity_percent": 71.8
  }
}
```

Reglas:

1. `payload` no debe ir vacio.
2. Si no hay `device_id`, usar `hardware_id`.
3. Si no hay conectividad, bufferizar y reintentar.
4. Si el sensor falla, no bloquear el resto de los devices.

## 4. Modulos que conviene crear en el edge

### Core edge modules

1. `auth`
   - Maneja la API key del edge.
   - Renueva o recarga configuracion.

2. `inventory`
   - Sincroniza devices desde el core.
   - Mantiene el cache local.

3. `presence`
   - Calcula y publica estados de presencia.

4. `commands`
   - Consume comandos pendientes.
   - Ejecuta acciones sobre el hardware.
   - Publica ACK.

5. `telemetry`
   - Normaliza lecturas de sensores.
   - Publica telemetry al core.

6. `connectivity`
   - Reintentos.
   - Backoff.
   - Buffer offline.

7. `observability`
   - Logs estructurados.
   - Contadores de exito/fallo.
   - Trazas si aplica.

## 5. Hoja de ruta por fases

### Fase 1: Base de conexion

Objetivo:

1. Autenticarse contra el core.
2. Descargar inventario.
3. Persistir cache local.

Entregables:

1. Cliente HTTP del core.
2. Configuracion de api key.
3. Modelo local de device.

### Fase 2: Presencia

Objetivo:

1. Publicar presence.
2. Detectar online/offline.
3. Reportar cambios de estado.

Entregables:

1. Scheduler o watcher de presencia.
2. Mapeo de estados a `ONLINE`, `OFFLINE`, `STANDBY`, `ERROR`.
3. Retry con backoff.

### Fase 3: Comandos

Objetivo:

1. Escuchar comandos.
2. Ejecutar sobre el hardware.
3. Confirmar resultado.

Entregables:

1. Consumer de Kafka o mecanismo equivalente.
2. Dispatcher por tipo de comando.
3. ACK al core.

### Fase 4: Telemetry

Objetivo:

1. Enviar lecturas del device.
2. Estandarizar payload.
3. Asegurar buffer offline.

Entregables:

1. Publicador de telemetry.
2. Normalizacion por sensor.
3. Reintentos y loteo si aplica.

### Fase 5: Robustez

Objetivo:

1. Idempotencia.
2. Reconciliacion.
3. Recuperacion automatica.

Entregables:

1. Deduplicacion por `command_id` y `telemetry_id` local.
2. Re-sync de inventario.
3. Health checks locales.

## 6. Contratos que el edge debe respetar

### Presence

- `device_id` o `hardware_id` obligatorio.
- `status` limitado a:
  - `ONLINE`
  - `OFFLINE`
  - `STANDBY`
  - `ERROR`

### Commands ack

- `device_id` obligatorio.
- `command_id` obligatorio.
- `status` limitado a:
  - `SENT`
  - `EXECUTED`
  - `FAILED`
- `failure_reason` obligatorio si `status` es `FAILED`.

### Telemetry

- `payload` obligatorio y no vacio.
- `device_id` o `hardware_id` obligatorio.
- `source` recomendado:
  - `edge`
  - `sensor`
  - `simulation`

## 7. Consideraciones de offline

Cuando el core no este disponible:

1. No detener la lectura de sensores.
2. Bufferizar telemetry.
3. Bufferizar presence si aplica.
4. Marcar comandos como pendientes localmente.
5. Reintentar con backoff exponencial.

Cuando el edge no pueda ejecutar hardware:

1. Responder `FAILED` al comando.
2. Registrar la razon.
3. Mantener vivo el resto del pipeline.

## 8. Orden sugerido de implementacion

1. Auth y sincronizacion de inventario.
2. Presence.
3. Commands ack.
4. Telemetry.
5. Buffer offline.
6. Observability y hardening.

## 9. Criterio de cierre

El edge puede considerarse integrado cuando:

1. Arranca con credenciales validas.
2. Sincroniza devices del core.
3. Reporta presencia.
4. Consume comandos.
5. Confirma ejecucion o fallo.
6. Envía telemetry util al core.
7. Se recupera correctamente tras perder conectividad.

