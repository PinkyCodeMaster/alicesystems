# web-dashboard

- Purpose: Browser-based advanced administration surface for Alice Home OS.
- Responsibilities: Sign into the local hub, review devices and entity state, inspect audit history, adjust advanced automation settings, and use the browser assistant interface.
- Interfaces: Reads and writes against `hub-api` over REST at `/api/v1` and talks to `assistant-runtime` over REST at `/api/v1`.
- Status: in progress.

## Run

```powershell
cd E:\alicesystems\apps\web-dashboard
bun install
bun run dev
```

Open:

- `http://127.0.0.1:3000`

## Targets

By default, Alice Web derives its API and assistant targets from the current browser host:

- `hub-api` on port `8000`
- `assistant-runtime` on port `8010`

Examples:

- browser at `http://127.0.0.1:3000` -> Home OS target `http://127.0.0.1:8000/api/v1`
- browser at `http://127.0.0.1:3000` -> assistant target `http://127.0.0.1:8010/api/v1`
- browser at `http://192.168.0.29:3000` -> Home OS target `http://192.168.0.29:8000/api/v1`
- browser at `http://192.168.0.29:3000` -> assistant target `http://192.168.0.29:8010/api/v1`

If you need to override those, set them in [`.env.local`](/e:/alicesystems/apps/web-dashboard/.env.local):

```env
NEXT_PUBLIC_ALICE_API_BASE_URL=http://192.168.0.29:8000/api/v1
NEXT_PUBLIC_ALICE_ASSISTANT_BASE_URL=http://192.168.0.29:8010/api/v1
```

Restart `bun run dev` after changing `.env.local`.

## Routes

Implemented now:

- `/`
  - first-run home setup when the hub is unclaimed
  - login when setup is already complete
  - hub and assistant reachability
  - stack health
  - home summary and quick links
- `/assistant`
  - browser assistant console
  - streaming assistant replies
  - session thread
  - assistant health
  - runtime memory snapshot
- `/devices`
  - device list
  - entity list
  - relay command buttons
- `/devices/[deviceId]`
  - device detail
  - entity state drill-down
  - recent audit for that device
- `/automations/auto-light`
  - auto-light settings editing
  - automation-related audit feed
- `/audit`
  - dedicated audit/event stream

Shared behaviors:

- local admin login
- WebSocket-triggered refresh with polling fallback
- light/dark/system theme toggle

## Known Gaps

- current live refresh uses WebSocket invalidation plus polling fallback, not full state streaming
- no browser voice input or output yet
- mobile remains the primary device-adoption surface
- mobile app code is still separate future work
