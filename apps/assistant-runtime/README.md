# assistant-runtime

- Purpose: Local assistant orchestration runtime for Alice.
- Responsibilities: Accept user requests, interpret them, and call Home OS tools without ever talking to devices directly.
- Interfaces: Uses authenticated Home OS REST APIs now; local STT/TTS/LLM integration comes next.
- Status: in progress.

## Current Scope

Implemented now:

- FastAPI runtime
- `GET /api/v1/health`
- `POST /api/v1/chat`
- deterministic intent handling for:
  - stack health
  - online devices
  - temperature queries
  - light level queries
  - turning the relay on/off through Home OS tool routes

Not implemented yet:

- STT
- TTS
- Ollama-based planning
- memory
- conversational session state

## Local Setup

```powershell
cd E:\alicesystems\apps\assistant-runtime
py -3.13 -m venv .alice
.\.alice\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

If you leave `HOME_OS_EMAIL` and `HOME_OS_PASSWORD` blank, the runtime will fall back to the `DEFAULT_ADMIN_*` values in [hub-api/.env](e:/alicesystems/apps/hub-api/.env).

## Run

```powershell
cd E:\alicesystems\apps\assistant-runtime
.\.alice\Scripts\Activate.ps1
python -m uvicorn assistant_runtime.main:app --host 0.0.0.0 --port 8010 --reload
```

PowerShell helper:

```powershell
.\scripts\run-assistant.ps1
```

Or start the full local Alice stack from the repo root:

```powershell
cd E:\alicesystems
.\tools\dev\start-local-stack.ps1
```

## Local URLs

- assistant health: `http://127.0.0.1:8010/api/v1/health`
- assistant docs: `http://127.0.0.1:8010/docs`

## Example Chat Request

```json
{
  "message": "turn on the bench light"
}
```

Example PowerShell call:

```powershell
Invoke-WebRequest `
  -Uri http://127.0.0.1:8010/api/v1/chat `
  -Method POST `
  -ContentType 'application/json' `
  -Body '{"message":"what devices are online"}' `
  -UseBasicParsing
```

## Known Gaps

- deterministic parser only
- no streaming responses
- no voice pipeline yet
- no memory layer yet
