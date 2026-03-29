# mobile-app

- Purpose: Primary mobile control surface for Alice in the home.
- Responsibilities: authenticate against Home OS, show a compact house overview, inspect projected device state, start device claim sessions, and provide basic relay control from a phone.
- Interfaces: talks to `hub-api` over REST and dashboard WebSocket invalidation today; assistant and notifications come later.
- Status: in progress.

## Current Status

Implemented now:

- Expo Router app scaffold
- Home OS login form on the `Home` tab
- configurable API base URL for simulator, emulator, or phone testing
- signed-in overview with site, stack-health, device count, entity count, and recent state changes
- `Devices` tab split into a list screen and a dedicated device detail screen
- device detail view with projected entities, recent audit, basic `switch.set` relay commands for writable boolean entities, and device removal
- `Add` tab with scan-first claim-session start, room selection, live claim-status polling, and local device handoff over the setup AP
- advanced QR-payload paste and manual claim details kept behind fallback controls for bench-device recovery
- Android-first native setup AP join/release path for onboarding in a development build
- live dashboard invalidation refresh for Overview, Devices, and Device Detail, with polling fallback

Not implemented yet:

- session persistence across app restarts
- assistant chat or push-to-talk
- notifications
- room-centric navigation

## How To Run

```powershell
cd E:\alicesystems\apps\mobile-app
bun install
bun run start
```

Useful variants:

- Android emulator: `bun run android`
- Android development build with native Wi-Fi onboarding: `bun run android:dev-build`
- iOS simulator: `bun run ios`
- web: `bun run web`
- repo root stack startup: `.\tools\dev\start-local-stack.ps1 -Mobile`

## Backend Target

The app resolves its backend like this:

- `EXPO_PUBLIC_ALICE_API_BASE_URL` if set
- otherwise `http://10.0.2.2:8000/api/v1` on Android
- otherwise `http://127.0.0.1:8000/api/v1`

For a real phone on your LAN, enter your PC IP in the Overview login form, for example:

```text
http://192.168.0.29:8000/api/v1
```

Backend inspection:

- API base URL: `http://127.0.0.1:8000/api/v1`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Current Tabs

- `Home`
  - login
  - site summary
  - stack health
  - recent projected state
- `Devices`
  - device list
  - per-device detail route
  - projected entity state
  - recent audit summary
  - basic relay on/off action for writable switch entities
- `Add`
  - QR scan for Alice bootstrap labels
  - guided claim flow for name + room
  - room selection from Home OS
  - claim session start
  - session status polling
  - Android development-build flow to join `AliceSetup-*`, post to `http://192.168.4.1/provision`, then release back to normal network
  - advanced manual fallback for Expo Go / non-Android builds while connected to the device setup AP

## Next Steps

- persist auth/session state locally
- add room navigation and room detail routes
- add assistant screen wired to `assistant-runtime`
- add mobile-specific tests

## Founder Workflow

- build locally
- verify against the live local stack
- review behavior in-house
- only then commit and push
