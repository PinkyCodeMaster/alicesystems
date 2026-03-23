# web-dashboard

- Purpose: Browser-based control and visibility surface for Alice Home OS during local development and early in-house testing.
- Responsibilities: Log into the hub, inspect devices and entities, view current state, review audit history, and change runtime settings like auto-light behavior.
- Interfaces: Reads and writes against `hub-api` over REST at `/api/v1`.
- Status: in progress.

## Run

```powershell
cd E:\alicesystems\apps\web-dashboard
bun install
bun run dev
```

Open:

- `http://127.0.0.1:3000`

## API Target

By default, the dashboard now derives its API target from the current browser host and port `8000`.

Examples:

- browser at `http://127.0.0.1:3000` -> API target `http://127.0.0.1:8000/api/v1`
- browser at `http://192.168.0.29:3000` -> API target `http://192.168.0.29:8000/api/v1`

If you need to override that, set:

```env
NEXT_PUBLIC_ALICE_API_BASE_URL=http://192.168.0.29:8000/api/v1
```

in [`.env.local`](e:/alicesystems/apps/web-dashboard/.env.local).

## Current Scope

Implemented now:

- local admin login
- device list
- entity list and current state
- relay command buttons
- recent audit history
- auto-light settings editing
- light/dark/system theme toggle

Not implemented yet:

- live WebSocket updates
- mobile-specific layouts
- assistant UI
- onboarding flows
- provisioning UX

## Known Gaps

- polling is still used instead of WebSocket streaming
- bad API targets still fail at runtime, but the login screen now shows the exact API target being used
- `.env.local` changes require restarting `bun run dev`
