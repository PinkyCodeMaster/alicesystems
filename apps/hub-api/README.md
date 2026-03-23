# hub-api

- Purpose: Alice Home OS runtime and source of truth for the local home system.
- Responsibilities: Own users, rooms, devices, entities, canonical state, audit events, authentication, MQTT ingest, and Home OS command flow.
- Interfaces: REST and OpenAPI now, MQTT ingest and MQTT command publish now, WebSocket and broader runtime services later.
- Status: in progress.

## Current Status

Implemented now:

- FastAPI app with local SQLite persistence
- Alembic migrations
- seeded default admin bootstrap
- JWT-backed local login
- `/auth/me`
- room CRUD subset for local testing
- canonical `entity_state` read/write endpoints
- audit logging for login, room creation, state updates, and device/MQTT events
- local seed command for demo data
- Windows PowerShell helper scripts
- offline evaluation from device last-seen timestamps
- MQTT command acknowledgement ingest
- persisted auto-light settings in SQLite
- stack-health endpoint for dashboard/operator visibility
- retained MQTT rehydration when state arrives before `hello`
- device detail API for dashboard drill-down
- WebSocket invalidation endpoint for dashboard refresh
- MQTT ingest handlers for:
  - `hello`
  - `availability`
  - `telemetry`
  - `state`
  - `ack`
- device and entity projection from MQTT `hello`
- Home OS command publish endpoint for writable entities
- bulk entity-state endpoint for dashboard polling
- live two-board house test completed with the current ESP32 sensor and relay nodes

Not implemented yet:

- real provisioning flow
- production-safe signed OTA flow
- automation engine
- full voice assistant pipeline
- full live state streaming to UI beyond invalidation
- mobile app code

## Dependencies

- Python `3.13`
- local venv named `.alice`
- PowerShell on Windows
- Docker Desktop if you want to run local Mosquitto through Docker Compose

## Clean Setup From Scratch

```powershell
cd E:\alicesystems\apps\hub-api
py -3.13 -m venv .alice
.\.alice\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
python -m alembic upgrade head
python -m app.scripts.seed_dev
```

If your `.env` already exists from an older local setup, compare it with `.env.example` and add the missing `MQTT_*` variables before testing broker integration.

## Start Commands

### Start The API

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

For in-house device debugging, prefer running without `--reload`:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Helper script:

```powershell
cd E:\alicesystems\apps\hub-api
.\scripts\run-api.ps1
```

One-window developer console:

```powershell
cd E:\alicesystems\apps\hub-api
.\scripts\dev-console.ps1 --serial-port COM5
```

That starts `hub-api`, tails `logs\hub-api.log`, and streams the ESP32 serial console in one window.

### Start Local Mosquitto

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
```

View broker logs:

```powershell
.\mqtt-logs.ps1
```

Stop broker:

```powershell
.\mqtt-down.ps1
```

To enable MQTT inside `hub-api`, set this in `E:\alicesystems\apps\hub-api\.env`:

```env
MQTT_ENABLED=true
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=alice/v1
```

Restart the API after changing `.env`.

Broker note:

- `hub-api` and the ESP32s must point to the same broker
- if your boards connect to Docker Mosquitto on your PC LAN IP, set `MQTT_HOST` in `hub-api` to that same LAN IP instead of `127.0.0.1`
- otherwise the boards and the hub will be on different brokers and no device messages will appear

### Start The Web Dashboard

```powershell
cd E:\alicesystems\apps\web-dashboard
bun install
Copy-Item .env.local.example .env.local -ErrorAction SilentlyContinue
bun run dev
```

Dashboard URL:

- `http://127.0.0.1:3000`

Optional auto-light defaults:

```env
AUTO_LIGHT_ENABLED=true
AUTO_LIGHT_SENSOR_ENTITY_ID=ent_dev_sensor_hall_01_illuminance
AUTO_LIGHT_TARGET_ENTITY_ID=ent_dev_light_bench_01_relay
AUTO_LIGHT_MODE=raw_high_turn_on
AUTO_LIGHT_ON_RAW=3000
AUTO_LIGHT_OFF_RAW=2600
```

These are now startup defaults only. The persisted setting lives in SQLite and is editable from:

- `GET /api/v1/system/auto-light`
- `PUT /api/v1/system/auto-light`

Optional development tracing:

```env
LOG_HTTP_REQUEST_BODIES=true
LOG_HTTP_REQUEST_BODY_MAX_BYTES=4096
LOG_HTTP_INCLUDE_DOCS_REQUESTS=false
```

With this enabled, mutating API requests are written to the local log with:

- a per-request `request_id`
- method, path, query, status code, duration
- redacted JSON body for `POST`, `PUT`, `PATCH`, and `DELETE`

Sensitive keys like `password`, `token`, `authorization`, `secret`, and `api_key` are masked before logging.

Log files:

- readable log: `logs\hub-api.log`
- structured JSON log: `logs\hub-api.jsonl`

## Seed Command

Safe to rerun:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m app.scripts.seed_dev
```

PowerShell helper:

```powershell
.\scripts\seed-dev.ps1
```

The seed creates:

- one site
- one founder/admin user
- `Office` and `Living Room`
- two placeholder devices
- three placeholder entities
- basic starter entity state

If you copied `.env.example` to `.env`, the seeded admin is:

- email: `admin@alice.systems`
- password: `change-me`

If your local `.env` uses different admin values, the seed will use those instead.

## Sync Admin After Changing `.env`

Changing `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`, or `DEFAULT_ADMIN_DISPLAY_NAME` in `.env` does not update an existing admin row by itself. Run the sync command after changing `.env`:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m app.scripts.sync_admin_from_env
```

PowerShell helper:

```powershell
.\scripts\sync-admin.ps1
```

Behavior:

- if the `.env` email already exists, that admin user is updated
- if there is exactly one admin user, it is renamed and its password is updated
- if multiple admin users already exist, a new default admin is created instead of renaming an ambiguous account

Recommended flow:

1. stop `hub-api`
2. run the sync command
3. start `hub-api`
4. log in with the new admin email and password

## Reset And Reseed

Stop the API first, then run:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
Remove-Item .\data\alice.db -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-shm -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-wal -ErrorAction SilentlyContinue
python -m alembic upgrade head
python -m app.scripts.seed_dev
```

PowerShell helper:

```powershell
.\scripts\reset-dev.ps1
```

If the reset helper reports that the DB is locked, stop `uvicorn` or any Python process using `alice.db`, then rerun it.

## Where To Inspect Things

- API base URL: `http://127.0.0.1:8000/api/v1`
- LAN API base URL: `http://192.168.0.29:8000/api/v1`
- Swagger UI: `http://127.0.0.1:8000/docs`
- LAN Swagger UI: `http://192.168.0.29:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- LAN API health: `http://192.168.0.29:8000/api/v1/health`
- web dashboard: `http://127.0.0.1:3000`
- SQLite DB: `E:\alicesystems\apps\hub-api\data\alice.db`
- local operational log: `E:\alicesystems\apps\hub-api\logs\hub-api.log`
- structured operational log: `E:\alicesystems\apps\hub-api\logs\hub-api.jsonl`
- app config: `E:\alicesystems\apps\hub-api\.env`
- example config: `E:\alicesystems\apps\hub-api\.env.example`
- broker config: `E:\alicesystems\infra\mosquitto\mosquitto.conf`
- broker compose file: `E:\alicesystems\infra\docker\docker-compose.yml`
- current API logs: the PowerShell window running `uvicorn`
- persisted API logs: `logs\hub-api.log`
- structured persisted logs: `logs\hub-api.jsonl`
- current broker logs: `.\mqtt-logs.ps1`

The local log file records:

- app startup and shutdown
- MQTT manager start and stop
- MQTT connect and disconnect events
- every HTTP request with a request ID
- audit events mirrored from the database layer
- device hello and availability updates
- automation failures

## Current Local Architecture

Running locally today:

- `hub-api` FastAPI process
- SQLite database in the `data/` folder
- Alembic migrations
- dev seed data
- optional Mosquitto broker via Docker Compose
- `web-dashboard` Next.js app

Implemented and live-tested in-house:

- MQTT message ingestion
- Home OS command publish to writable entities
- device/entity projection from MQTT `hello`
- device availability updates
- retained state reconciliation after hub restart
- relay command acknowledgement ingestion
- auto-light acting on live light sensor readings
- dashboard stack health and device detail APIs

Not implemented yet:

- mobile app
- production-safe OTA
- full device provisioning
- production device auth

## MQTT Contract For Current ESP32 Work

Current topic set:

- `alice/v1/device/{device_id}/hello`
- `alice/v1/device/{device_id}/availability`
- `alice/v1/device/{device_id}/telemetry`
- `alice/v1/device/{device_id}/state`
- `alice/v1/device/{device_id}/ack`
- `alice/v1/device/{device_id}/cmd`

Expected `hello` payload shape:

```json
{
  "name": "Hall Sensor",
  "model": "alice.sensor.env.s1",
  "device_type": "sensor_node",
  "fw_version": "0.1.0",
  "capabilities": [
    {
      "capability_id": "temperature",
      "kind": "sensor.temperature",
      "name": "Temperature",
      "slug": "temperature",
      "writable": 0,
      "traits": {"unit": "C"}
    },
    {
      "capability_id": "motion",
      "kind": "sensor.motion",
      "name": "Motion",
      "slug": "motion",
      "writable": 0,
      "traits": {}
    }
  ]
}
```

Expected state or telemetry examples:

```json
{"capability":"temperature","celsius":21.2}
{"capability":"motion","motion":true}
{"capability":"relay","on":true}
```

Command example published by Home OS:

```json
{
  "cmd_id": "cmd_...",
  "ts": "2026-03-23T13:40:00+00:00",
  "type": "entity.command",
  "target_entity_id": "ent_dev_test_light_01_relay",
  "name": "switch.set",
  "params": {
    "on": true
  }
}
```

## Current Testing Scope

Current automated tests cover:

- app boot
- migrations during startup
- seeded admin login
- protected `/auth/me`
- protected room creation
- entity state write/read flow
- audit event listing
- MQTT `hello` projection into devices/entities
- MQTT state projection into `entity_state`
- MQTT ack ingestion into audit history
- Home OS command publish endpoint behavior
- persisted auto-light settings API
- device offline timeout evaluation
- stack health endpoint
- retained-message rehydration handling
- device detail endpoint shape

Current gaps:

- no live broker integration test in CI
- no live ESP32 test in CI
- no provisioning flow yet
- no production OTA flow yet
- no UI tests yet
- no end-to-end assistant integration tests in CI yet

## ESP32 Test Plan

Target local hardware:

- ESP32 sensor node with temperature, light, and PIR
- ESP32 actuator node with LED acting as light/relay

Current plan:

- sensor node sends `hello` on boot with capability list
- sensor node publishes `telemetry` and/or `state`
- relay/light node sends `hello` on boot with relay capability
- Home OS projects those into `devices` and `entities`
- Home OS command endpoint publishes `switch.set` to the light node `cmd` topic

Current status:

- current Home OS integration path implemented in `hub-api`
- live in-house ESP32 sensor + relay integration verified
- current working devices are `dev_sensor_hall_01` and `dev_light_bench_01`

## Founder Workflow

Required workflow for this repo:

1. develop locally
2. test locally
3. verify behavior with founder
4. only then commit
5. only then push

## Known Gaps

- no requirements lockfile yet
- no separate worker runtime yet
- no structured logging pipeline yet
- no frontend app code yet
- MQTT currently uses anonymous local broker config for bench testing only
- production device auth, provisioning, and OTA are still pending

## Next Steps

- add production-grade provisioning and device auth
- add signed OTA architecture
- add richer automation rules and editing UX
- deepen assistant tool coverage
- add mobile app
