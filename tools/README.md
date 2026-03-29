# tools

- Purpose: Internal engineering tooling.
- Will contain: Dev scripts, build helpers, QA tooling, and manufacturing support utilities.
- Responsibilities: Keep operational scripts and helper tools out of product runtime code.
- Interfaces: Used across software, firmware, hardware, and manufacturing workflows.
- Status: in progress.

## Useful Helpers

- `dev/start-local-backend.ps1`: preferred local backend command for real Alice product work; runs `hub-api`, `assistant-runtime`, and local Mosquitto with logs visible in one console
- `qa/generate-device-qr.ps1`: generate a scannable PNG from the `ALICE_DEVICE_QR` JSON emitted by a bench ESP32 over serial.
