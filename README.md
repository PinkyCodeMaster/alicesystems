# Alice Systems Monorepo

This repository is the long-lived platform monorepo for Alice Systems.

- Purpose: Hold the software, firmware, hardware, manufacturing, ML, compliance, and documentation assets for the Alice local-first assistant and Home OS platform.
- Will contain: Hub runtime, assistant runtime, mobile and web clients, device firmware, hardware product definitions, manufacturing assets, compliance evidence, and future interface product lines.
- Responsibilities: Preserve clear ownership boundaries between Home OS, assistant orchestration, device runtime, hardware programs, and future ecosystem products.
- Interfaces: Shared contracts live under `packages/contracts` and `packages/device-capabilities`; runtime integration happens through REST, WebSocket, MQTT, signed OTA, and versioned schemas.
- Status: in progress.

See [docs/architecture/alice-mvp-v1-blueprint.md](docs/architecture/alice-mvp-v1-blueprint.md) for the MVP system blueprint.
