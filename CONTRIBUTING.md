# Contributing to Alice Systems

Alice is a local-first household operating system. Contributions should strengthen the real product spine that already exists instead of adding parallel scaffolding, fake product surfaces, or bench-only defaults in primary flows.

## Working principles

- Keep the hub as the canonical local authority for system state.
- Keep mobile as the primary user surface and web as the advanced or admin surface.
- Prefer improving existing runtime paths over creating new ones.
- Prefer real product wording over debug or prototype wording in exposed UX.

## Golden path for local development

1. Start the local backend with `.\tools\dev\start-local-backend.ps1`.
2. This should bring up the working Alice backend stack: `hub-api`, `assistant-runtime`, and `mosquitto`.
3. Start the mobile app or web dashboard separately, depending on the surface you are changing.
4. Verify the real onboarding and device flows before proposing additional tooling or abstractions.

## Before opening a pull request

- Keep changes scoped to one problem.
- Add or update tests where the repo already has coverage.
- Update runtime docs or app README files if you changed the supported local path.
- Do not commit secrets, generated `.env` files, or device-specific credentials.
- Call out any change that impacts provisioning, MQTT contracts, auth, or database shape.

## Review expectations

- Product-facing flows should not expose placeholder copy, dead ends, or obvious bench-only controls unless they are deliberately hidden behind advanced/debug affordances.
- Runtime changes should preserve local-first behavior and visible local logs.
- New infrastructure should be justified by an immediate working need, not a target-state idea.

## Security reporting

Do not open public issues for vulnerabilities. Follow the process in `SECURITY.md`.
