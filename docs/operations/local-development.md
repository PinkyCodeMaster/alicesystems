# Local Development

## Purpose

This document is the Windows-first local developer guide for Alice Systems. It gets a clean machine from zero to a working local `hub-api`, `assistant-runtime`, dashboard, optional Mosquitto, and a repeatable reset path.

## Current Local Architecture

Runs locally today:

- `hub-api` FastAPI service
- `assistant-runtime` FastAPI service
- SQLite database
- Alembic migrations
- local seed data
- optional Mosquitto broker via Docker Compose
- `web-dashboard`

Implemented and locally testable in code now:

- MQTT ingest handlers
- device/entity projection from MQTT `hello`
- canonical state writes from MQTT `telemetry` and `state`
- Home OS MQTT command publish path for writable entities
- MQTT command acknowledgement ingest
- persisted auto-light settings API
- offline device evaluation from last-seen timestamps

Not runnable yet:

- `mobile-app`
- live provisioning flow

Prototype firmware now exists for:

- `firmware/esp32-sensor-node`
- `firmware/esp32-relay-node`

Prototype OTA now exists for:

- `firmware/esp32-sensor-node`
- `firmware/esp32-relay-node`

## Clean Setup From Scratch

### Hub API

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

If `.env` already exists from an older setup, compare it with `.env.example` and add the missing `MQTT_*` keys.

## Start Commands

### Backend API

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Helper script:

```powershell
cd E:\alicesystems\apps\hub-api
.\scripts\run-api.ps1
```

### One-Window Dev Console

```powershell
cd E:\alicesystems\apps\hub-api
.\scripts\dev-console.ps1 --serial-port COM5
```

This combines:

- `hub-api` process output
- readable `hub-api.log`
- ESP32 serial monitor

Optional broker logs:

```powershell
.\scripts\dev-console.ps1 --serial-port COM5 --broker-logs
```

### Start The Whole Local Stack

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1
```

This does all of the following:

- starts Docker Mosquitto
- runs hub migrations
- launches `hub-api` in a new PowerShell window
- launches `assistant-runtime` in a new PowerShell window
- launches `web-dashboard` in a new PowerShell window

After that, the ESP32 boards should reconnect automatically. Use `EN/RST` only if you are bench-debugging a board that has stopped publishing.

### Local MQTT Broker

Start broker:

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

Enable broker use in `E:\alicesystems\apps\hub-api\.env`:

```env
MQTT_ENABLED=true
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=alice/v1
```

Restart the API after changing `.env`.

Important:

- `hub-api` and the ESP32s must point to the same broker
- if your boards connect to Docker Mosquitto on the PC LAN IP, set `MQTT_HOST` in `hub-api` to that same LAN IP instead of `127.0.0.1`
- otherwise the hub and the boards will be on different brokers and no device messages will appear

Optional startup defaults for auto-light:

```env
AUTO_LIGHT_ENABLED=true
AUTO_LIGHT_SENSOR_ENTITY_ID=ent_dev_sensor_hall_01_illuminance
AUTO_LIGHT_TARGET_ENTITY_ID=ent_dev_light_bench_01_relay
AUTO_LIGHT_MODE=raw_high_turn_on
AUTO_LIGHT_ON_RAW=3000
AUTO_LIGHT_OFF_RAW=2600
```

These are startup defaults only. The persisted setting now lives in SQLite and is editable from the dashboard or `/api/v1/system/auto-light`.

Optional development tracing:

```env
LOG_HTTP_REQUEST_BODIES=true
LOG_HTTP_REQUEST_BODY_MAX_BYTES=4096
LOG_HTTP_INCLUDE_DOCS_REQUESTS=false
```

This adds request-level trace to `logs\hub-api.log`, including:

- request ID
- method and path
- query string
- response status
- request duration
- redacted JSON body for mutating requests

### Web Dashboard

```powershell
cd E:\alicesystems\apps\web-dashboard
bun install
Copy-Item .env.local.example .env.local -ErrorAction SilentlyContinue
bun run dev
```

Local URL:

- `http://127.0.0.1:3000`

If you do not want separate manual steps, use:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1
```

### Assistant Runtime

```powershell
cd E:\alicesystems\apps\assistant-runtime
py -3.13 -m venv .alice
.\.alice\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
python -m uvicorn assistant_runtime.main:app --host 0.0.0.0 --port 8010
```

Helper script:

```powershell
cd E:\alicesystems\apps\assistant-runtime
.\scripts\run-assistant.ps1
```

### Mobile App

Not implemented yet. No runnable command exists.

### Worker

No separate worker implementation exists yet. No runnable command exists.

## Seed Commands

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m app.scripts.seed_dev
```

Helper script:

```powershell
.\scripts\seed-dev.ps1
```

Seed behavior:

- safe to rerun
- ensures one site
- ensures founder/admin user
- ensures `Office` and `Living Room`
- ensures placeholder sensor and light devices
- ensures placeholder entities and starter state

If you copied `.env.example`, the seeded login is:

- email: `admin@alice.systems`
- password: `change-me`

If your `.env` overrides those values, use the ones in `.env`.

## Sync Admin After `.env` Changes

If you changed `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`, or `DEFAULT_ADMIN_DISPLAY_NAME` in `apps\hub-api\.env`, run:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m app.scripts.sync_admin_from_env
```

Helper script:

```powershell
.\scripts\sync-admin.ps1
```

Recommended flow:

1. stop `hub-api`
2. run the sync command
3. start `hub-api`
4. log in with the new admin credentials

The sync command behaves like this:

- if the new email already exists, that admin is updated
- if there is exactly one admin in the DB, it is renamed to the new `.env` email
- if multiple admins already exist, a new default admin is created instead of renaming an ambiguous account

## Reset And Reseed

Stop the API first.

Manual reset:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
Remove-Item .\data\alice.db -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-shm -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-wal -ErrorAction SilentlyContinue
python -m alembic upgrade head
python -m app.scripts.seed_dev
```

Helper script:

```powershell
.\scripts\reset-dev.ps1
```

If reset fails because the DB is locked, stop `uvicorn` or any Python process holding `alice.db` open and rerun the command.

## Where To Inspect Things

- API URL: `http://127.0.0.1:8000/api/v1`
- LAN API URL: `http://192.168.0.29:8000/api/v1`
- assistant URL: `http://127.0.0.1:8010/api/v1`
- LAN assistant URL: `http://192.168.0.29:8010/api/v1`
- Swagger UI: `http://127.0.0.1:8000/docs`
- LAN Swagger UI: `http://192.168.0.29:8000/docs`
- assistant docs: `http://127.0.0.1:8010/docs`
- LAN assistant docs: `http://192.168.0.29:8010/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- LAN health: `http://192.168.0.29:8000/api/v1/health`
- web dashboard: `http://127.0.0.1:3000`
- SQLite DB: `E:\alicesystems\apps\hub-api\data\alice.db`
- local operational log: `E:\alicesystems\apps\hub-api\logs\hub-api.log`
- structured operational log: `E:\alicesystems\apps\hub-api\logs\hub-api.jsonl`
- config file: `E:\alicesystems\apps\hub-api\.env`
- example config: `E:\alicesystems\apps\hub-api\.env.example`
- broker config: `E:\alicesystems\infra\mosquitto\mosquitto.conf`
- broker compose file: `E:\alicesystems\infra\docker\docker-compose.yml`
- local helper scripts: `E:\alicesystems\apps\hub-api\scripts\`
- current API logs: in the PowerShell window running `uvicorn`
- persisted API logs: `E:\alicesystems\apps\hub-api\logs\hub-api.log`
- structured persisted logs: `E:\alicesystems\apps\hub-api\logs\hub-api.jsonl`
- current broker logs: in `.\mqtt-logs.ps1`

When debugging a bad action from a family member, start with the `request_id` from the log line and then follow:

1. `http.request`
2. any matching `alice.audit` event
3. any MQTT or automation warning around the same time

## Current Testing Scope

Working now:

- booting the API from a clean venv
- running Alembic migrations
- seeding local dev data
- local admin login
- `/auth/me`
- protected room creation
- entity state write/read
- audit event listing
- MQTT `hello` projection into `devices` and `entities`
- MQTT state projection into `entity_state`
- Home OS command publish endpoint behavior
- MQTT ack ingestion
- persisted auto-light settings API
- device offline timeout evaluation
- Next.js web dashboard build

Not yet field-verified:

- live Mosquitto plus live ESP32 sensor node
- live Mosquitto plus live ESP32 LED/light node
- retained state reconciliation
- command acknowledgement handling
- assistant runtime against live Home OS

Not implemented yet:

- mobile app
- automation execution
- provisioning flows
- production-safe signed OTA

## ESP32 Test Plan Placeholder

Target hardware:

- ESP32 sensor node with temperature, light, and PIR
- ESP32 LED/light node acting as the first actuator

Planned local path:

- Home OS ingest from `alice/v1/device/{device_id}/hello`
- Home OS ingest from `alice/v1/device/{device_id}/telemetry`
- Home OS ingest from `alice/v1/device/{device_id}/state`
- Home OS ingest from `alice/v1/device/{device_id}/ack`
- Home OS command publish to `alice/v1/device/{device_id}/cmd`

Suggested first real test:

1. start Mosquitto
2. set `MQTT_ENABLED=true`
3. restart `hub-api`
4. publish a manual `hello` message from a test client
5. confirm device and entity creation via `/api/v1/devices` and `/api/v1/entities`
6. publish a manual sensor state message
7. confirm `/api/v1/entities/{id}/state`
8. call the command endpoint for the LED/light entity
9. confirm the command appears on the device command topic

Current status:

- prototype integration path implemented
- live in-house ESP32 verification is the next hardware milestone

For the exact board flash and verification steps, use [esp32-bench-test.md](e:/alicesystems/docs/operations/esp32-bench-test.md).

For the prototype over-the-air update path, use [esp32-ota.md](e:/alicesystems/docs/operations/esp32-ota.md).

## Founder Workflow

Required workflow:

1. develop locally
2. run tests locally
3. verify behavior on the local machine and in-house setup
4. only then commit
5. only then push
