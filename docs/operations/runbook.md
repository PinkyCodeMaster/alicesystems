# Runbook

## Quick Start

```powershell
cd E:\alicesystems\apps\hub-api
py -3.13 -m venv .alice
.\.alice\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
python -m alembic upgrade head
python -m app.scripts.seed_dev
python -m uvicorn app.main:app --reload
```

## One Command Start

```powershell
cd E:\alicesystems
.\tools\dev\start-local-backend.ps1
```

This starts the current local Alice backend:

- Docker Mosquitto
- `hub-api`
- `assistant-runtime`

The ESP32 boards should reconnect automatically. Manual reset is only for debugging or forcing a fresh `hello`.

## Quick MQTT Bring-Up

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
.\mqtt-logs.ps1
```

Then set `MQTT_ENABLED=true` in `E:\alicesystems\apps\hub-api\.env` and restart `hub-api`.

If your ESP32s connect to Docker Mosquitto on the PC LAN IP, set:

```env
MQTT_HOST=<pc-lan-ip>
```

Do not leave `hub-api` on `127.0.0.1` while the boards use a different broker.

## Quick Reset

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
Remove-Item .\data\alice.db -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-shm -ErrorAction SilentlyContinue
Remove-Item .\data\alice.db-wal -ErrorAction SilentlyContinue
python -m alembic upgrade head
python -m app.scripts.seed_dev
```

Or:

```powershell
.\scripts\reset-dev.ps1
```

## Helper Scripts

```powershell
cd E:\alicesystems\apps\hub-api
.\scripts\run-api.ps1
.\scripts\seed-dev.ps1
.\scripts\reset-dev.ps1
```

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
.\mqtt-down.ps1
.\mqtt-logs.ps1
```

```powershell
cd E:\alicesystems
.\tools\dev\start-local-backend.ps1
.\tools\dev\stop-local-backend.ps1
```

## Local URLs

- API base: `http://127.0.0.1:8000/api/v1`
- assistant base: `http://127.0.0.1:8010/api/v1`
- Swagger UI: `http://127.0.0.1:8000/docs`
- assistant docs: `http://127.0.0.1:8010/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- web dashboard: `http://127.0.0.1:3000`
- assistant session history: `http://127.0.0.1:8010/api/v1/sessions/<session_id>/messages`

## Local Files

- DB: `E:\alicesystems\apps\hub-api\data\alice.db`
- log file: `E:\alicesystems\apps\hub-api\logs\hub-api.log`
- config: `E:\alicesystems\apps\hub-api\.env`
- requirements: `E:\alicesystems\apps\hub-api\requirements.txt`
- dev requirements: `E:\alicesystems\apps\hub-api\requirements-dev.txt`
- broker config: `E:\alicesystems\infra\mosquitto\mosquitto.conf`
- broker compose: `E:\alicesystems\infra\docker\docker-compose.yml`

## Current Runnable Components

- `hub-api`: runnable now
- `mosquitto`: runnable now through Docker Compose
- `assistant-runtime`: runnable now
- `web-dashboard`: runnable now
- `mobile-app`: runnable separately
- worker: not implemented yet

## Current Seeded Login

If you copied `.env.example`:

- email: `admin@alice.systems`
- password: `change-me`

If your `.env` differs, use the values there.

## Current MQTT Topics

- `alice/v1/device/{device_id}/hello`
- `alice/v1/device/{device_id}/availability`
- `alice/v1/device/{device_id}/telemetry`
- `alice/v1/device/{device_id}/state`
- `alice/v1/device/{device_id}/ack`
- `alice/v1/device/{device_id}/cmd`

## Dashboard

```powershell
cd E:\alicesystems\apps\web-dashboard
bun install
Copy-Item .env.local.example .env.local -ErrorAction SilentlyContinue
bun run dev
```

Current dashboard scope:

- login
- stack health
- device list
- device detail pages
- relay control
- audit view
- auto-light settings

## Assistant Runtime

Current assistant scope:

- Home OS health dependency checks
- session-backed chat threads
- deterministic tool routing
- Ollama planner with fallback

Suggested assistant `.env` for the current machine:

```env
ASSISTANT_MODE=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
```

## ESP32 Bench Test

- sensor firmware: [esp32-sensor-node](e:/alicesystems/firmware/esp32-sensor-node)
- relay firmware: [esp32-relay-node](e:/alicesystems/firmware/esp32-relay-node)
- bench guide: [esp32-bench-test.md](e:/alicesystems/docs/operations/esp32-bench-test.md)
