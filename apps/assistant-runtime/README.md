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
- `GET /api/v1/sessions/{session_id}/messages`
- SQLite-backed session/thread history
- deterministic intent handling for:
  - stack health
  - online devices
  - temperature queries
  - light level queries
  - auto-light status queries
  - enabling/disabling auto-light through Home OS tool routes
  - auto-light threshold edits through Home OS tool routes
  - recent audit event summaries
  - turning the relay on/off through Home OS tool routes
- optional Ollama planner with deterministic fallback
- response debug block showing actual planner path and fallback status

Not implemented yet:

- STT
- TTS
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

If you want the assistant to use a local model first, set:

```env
ASSISTANT_MODE=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=<your-local-model>
```

`auto` means:

- try Ollama planner first
- fall back to deterministic mode if Ollama is unavailable or fails

`deterministic` means:

- skip Ollama entirely
- use only the local rule-based tool selector

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

Health now includes dependency status for:

- Home OS reachability
- Ollama reachability

## Example Chat Request

```json
{
  "message": "turn on the bench light",
  "session_id": "sess_optional_existing_thread"
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

Then inspect the thread:

```powershell
Invoke-WebRequest `
  -Uri http://127.0.0.1:8010/api/v1/sessions/<session_id>/messages `
  -UseBasicParsing
```

Inspect whether a reply came from Ollama or deterministic fallback in:

- `mode`
- `debug.planner_source`
- `debug.fallback_used`
- `debug.planner_error`

## Known Gaps

- no voice pipeline yet
- no streaming responses
- no memory layer yet
- no assistant support yet for choosing auto-light sensor/target mappings or richer Home OS workflows
