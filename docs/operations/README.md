# operations

- Purpose: Alice local run, reset, support, and operator workflow documentation.
- Responsibilities: Make the current system easy to start from scratch on a Windows development machine and easy to inspect before committing.
- Interfaces: Covers `hub-api` and local Mosquitto now and will expand to web, mobile, assistant runtime, and hardware workflows later.
- Status: in progress.

## Documents

- [local-development.md](e:/alicesystems/docs/operations/local-development.md): full clean-start local setup and daily developer workflow
- [runbook.md](e:/alicesystems/docs/operations/runbook.md): quick operational commands and URLs
- [esp32-bench-test.md](e:/alicesystems/docs/operations/esp32-bench-test.md): fastest path to the first real two-board MQTT test
- [esp32-ota.md](e:/alicesystems/docs/operations/esp32-ota.md): prototype over-the-air firmware update workflow for the current ESP32 boards

## Current Scope

Runnable today:

- `apps/hub-api`
- `apps/web-dashboard`
- local Mosquitto broker via `infra/docker/docker-compose.yml`

Scaffold only today:

- `apps/mobile-app`
- assistant runtime local ops
- MQTT/device ops
