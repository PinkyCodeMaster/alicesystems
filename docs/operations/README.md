# operations

- Purpose: Alice local run, reset, support, and operator workflow documentation.
- Responsibilities: Make the current system easy to start from scratch on a Windows development machine and easy to inspect before committing.
- Interfaces: Covers `hub-api`, `assistant-runtime`, `web-dashboard`, local Mosquitto, OTA bench flows, and current ESP32 hardware workflows.
- Status: in progress.

## Documents

- [local-development.md](e:/alicesystems/docs/operations/local-development.md): full clean-start local setup and daily developer workflow
- [runbook.md](e:/alicesystems/docs/operations/runbook.md): quick operational commands and URLs
- [esp32-bench-test.md](e:/alicesystems/docs/operations/esp32-bench-test.md): fastest path to the first real two-board MQTT test
- [esp32-ota.md](e:/alicesystems/docs/operations/esp32-ota.md): prototype over-the-air firmware update workflow for the current ESP32 boards
- [2026-03-23-status.md](e:/alicesystems/docs/operations/2026-03-23-status.md): end-of-day status snapshot of the working local MVP slice

## Current Scope

Runnable today:

- `apps/hub-api`
- `apps/assistant-runtime`
- `apps/web-dashboard`
- local Mosquitto broker via `infra/docker/docker-compose.yml`
- current ESP32 sensor + relay prototype hardware loop

Still scaffold or future-only:

- `apps/mobile-app`
- TV/wall/wearable/car interfaces
- manufacturing/compliance programs
