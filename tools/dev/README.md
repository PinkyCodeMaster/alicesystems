# dev

- Purpose: Developer workflow tooling for running Alice locally without juggling multiple terminals.
- Responsibilities: Start local services, stream logs, expose serial output from bench hardware, and reduce friction during in-house debugging.
- Interfaces: Supports `apps/hub-api`, `apps/assistant-runtime`, `apps/web-dashboard`, local Mosquitto, and ESP32 USB serial monitoring.
- Status: active local runtime tooling.

## Current Tools

- [alice_dev_console.py](e:/alicesystems/tools/dev/alice_dev_console.py): one-window developer console for `hub-api`, hub logs, optional broker logs, and one ESP32 serial port
- [start-local-backend.ps1](e:/alicesystems/tools/dev/start-local-backend.ps1): native source-of-truth backend startup for local product work. Stops conflicting Docker practice containers, runs migrations, starts native Mosquitto, `hub-api`, and `assistant-runtime` in one console.
- [stop-local-backend.ps1](e:/alicesystems/tools/dev/stop-local-backend.ps1): stops the native backend console processes and Mosquitto.
- [start-local-stack.ps1](e:/alicesystems/tools/dev/start-local-stack.ps1): starts Mosquitto, runs hub migrations, launches `hub-api`, launches `assistant-runtime`, launches the Next.js dashboard, and optionally launches the Expo mobile app with `-Mobile`
- [stop-local-stack.ps1](e:/alicesystems/tools/dev/stop-local-stack.ps1): stops the local broker plus the current `uvicorn`, `next dev`, and `expo start` processes

## Product-First Backend

Recommended from the repo root for almost all backend and provisioning work:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-backend.ps1
```

This is the preferred local backend path when working on the real product flow instead of the Docker practice stack.

It will:

- stop conflicting Docker practice containers on ports `8000`, `8010`, and `1883`
- run `alembic upgrade head`
- start native Mosquitto with the repo config
- start `hub-api`
- start `assistant-runtime`
- keep all backend logs in one console

Stop it with:

```powershell
cd E:\alicesystems
.\tools\dev\stop-local-backend.ps1
```

## One-Window Dev Console

Recommended command from [apps/hub-api](e:/alicesystems/apps/hub-api):

```powershell
.\scripts\dev-console.ps1
```

That starts:

- `hub-api`
- readable `hub-api.log` tail
- ESP32 serial monitor on `COM5`

Optional broker logs too:

```powershell
.\scripts\dev-console.ps1 --broker-logs
```

If the ESP32 is on a different port:

```powershell
.\scripts\dev-console.ps1 --serial-port COM7
```

## Start The Full Local Stack

Use this only when you explicitly want the UI processes opened as well:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1
```

That will:

- start Docker Mosquitto
- run `alembic upgrade head`
- open a PowerShell window for `hub-api`
- open a PowerShell window for `assistant-runtime`
- open a PowerShell window for `web-dashboard` with `bun run dev`

This is not the default Alice backend path. Prefer `start-local-backend.ps1` unless you need the extra UI windows started for you.

The ESP32 boards should reconnect automatically if they are already powered. Manual reset is only for bench debugging.

To include the mobile app too:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1 -Mobile
```

That also opens a PowerShell window for `apps/mobile-app` with `bun run start`.

## Stop The Full Local Stack

```powershell
cd E:\alicesystems
.\tools\dev\stop-local-stack.ps1
```

## Dependencies

- local `.alice` venv in `apps/hub-api`
- local `.alice` venv in `apps/assistant-runtime`
- `pyserial` installed through `requirements-dev.txt`
- optional Docker Desktop for broker log streaming

## Known Gaps

- one serial port at a time right now
- no GUI yet
- no automatic COM port detection yet
