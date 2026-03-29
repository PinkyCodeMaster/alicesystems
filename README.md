# Alice Systems Monorepo

This repository is the long-lived platform monorepo for Alice Systems.

- Purpose: Hold the software, firmware, hardware, manufacturing, ML, compliance, and documentation assets for the Alice local-first assistant and Home OS platform.
- Will contain: Hub runtime, assistant runtime, mobile and web clients, device firmware, hardware product definitions, manufacturing assets, compliance evidence, and future interface product lines.
- Responsibilities: Preserve clear ownership boundaries between Home OS, assistant orchestration, device runtime, hardware programs, and future ecosystem products.
- Interfaces: Shared contracts live under `packages/contracts` and `packages/device-capabilities`; runtime integration happens through REST, WebSocket, MQTT, signed OTA, and versioned schemas.
- Status: in progress.

See [docs/architecture/alice-mvp-v1-blueprint.md](docs/architecture/alice-mvp-v1-blueprint.md) for the MVP system blueprint.

## Current Working Slice

Working locally today:

- [hub-api](e:/alicesystems/apps/hub-api/README.md): FastAPI Home OS with SQLite, MQTT ingest, device/entity projection, stack health, and audit logging
- [web-dashboard](e:/alicesystems/apps/web-dashboard/README.md): bun-based Next.js control surface with login, stack health, device detail views, relay control, and auto-light settings
- [assistant-runtime](e:/alicesystems/apps/assistant-runtime/README.md): local assistant runtime with session history, deterministic tool routing, and Ollama planning with fallback
- [operations docs](e:/alicesystems/docs/operations/README.md): Windows-first local start/stop, MQTT, OTA, and end-of-day status

## Run Alice Locally

For real product work, the local backend path is:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-backend.ps1
```

That starts the native Alice backend in one console with visible logs:

- `hub-api`
- `assistant-runtime`
- local Mosquitto

Use `.\tools\dev\start-local-stack.ps1` only when you explicitly also want the web UI or mobile client launched for UI work. The Docker practice stack is a separate rehearsal environment, not the default local product runtime.

End-of-day project status for March 23, 2026:

- [2026-03-23-status.md](e:/alicesystems/docs/operations/2026-03-23-status.md)
