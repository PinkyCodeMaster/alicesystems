# mobile-app

- Purpose: Primary mobile control surface for Alice in the home.
- Responsibilities: Onboarding, room control, notifications, push-to-talk assistant access, and future phone-assisted device linking.
- Interfaces: Will talk to `hub-api` over REST and WebSocket and later assist with QR-based onboarding flows.
- Status: planned scaffold only.

## Current Status

This folder exists in the monorepo and is intentionally reserved, but there is no runnable Expo app code here yet.

## How To Run

There is no current run command because the mobile app is not implemented yet.

Current backend to target once the app exists:

- API base URL: `http://127.0.0.1:8000/api/v1`
- Swagger UI for backend inspection: `http://127.0.0.1:8000/docs`

## Dependencies

Planned later:

- Node.js
- Expo CLI or `npx expo`
- local Alice Home OS backend running

## Known Gaps

- no `package.json`
- no Expo app scaffold
- no auth flow
- no device onboarding UI
- no assistant UI

## Next Steps

- create Expo app scaffold
- add login and home screens
- connect to local `hub-api`
- add phone-assisted setup flow placeholders for TVs, watches, and devices

## Founder Workflow

- build locally
- verify against live backend
- review behavior in-house
- only then commit and push
