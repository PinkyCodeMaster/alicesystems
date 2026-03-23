# dev

- Purpose: Developer workflow tooling for running Alice locally without juggling multiple terminals.
- Responsibilities: Start local services, stream logs, expose serial output from bench hardware, and reduce friction during in-house debugging.
- Interfaces: Supports `apps/hub-api`, local Mosquitto, and ESP32 USB serial monitoring.
- Status: prototype.

## Current Tools

- [alice_dev_console.py](e:/alicesystems/tools/dev/alice_dev_console.py): one-window developer console for `hub-api`, hub logs, optional broker logs, and one ESP32 serial port
- [start-local-stack.ps1](e:/alicesystems/tools/dev/start-local-stack.ps1): starts Mosquitto, runs hub migrations, launches `hub-api`, and launches the Next.js dashboard
- [stop-local-stack.ps1](e:/alicesystems/tools/dev/stop-local-stack.ps1): stops the local broker plus the current `uvicorn` and `next dev` processes

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

Recommended from the repo root:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1
```

That will:

- start Docker Mosquitto
- run `alembic upgrade head`
- open a PowerShell window for `hub-api`
- open a PowerShell window for `web-dashboard` with `bun run dev`

Then power or reset the ESP32 boards so they reconnect to the broker and re-announce.

## Stop The Full Local Stack

```powershell
cd E:\alicesystems
.\tools\dev\stop-local-stack.ps1
```

## Dependencies

- local `.alice` venv in `apps/hub-api`
- `pyserial` installed through `requirements-dev.txt`
- optional Docker Desktop for broker log streaming

## Known Gaps

- one serial port at a time right now
- no GUI yet
- no automatic COM port detection yet
