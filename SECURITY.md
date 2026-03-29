# Security Policy

## Reporting a vulnerability

Do not open a public issue for suspected security problems.

Report privately with:

- affected component or path
- reproduction steps
- impact assessment
- logs or screenshots with secrets removed

If you do not yet have a dedicated private reporting channel, establish one before inviting broader outside contributions.

## Supported versions

Alice is under active development. The default branch is the only supported version for security fixes.

## Current security posture

- Alice is designed to run local-first inside the home network.
- Hub auth, audit logging, and request redaction are already part of the runtime.
- Device provisioning and service-to-service trust are still being hardened.

## Near-term hardening priorities

- keep dependency updates flowing through Dependabot and CI
- run CodeQL on the default branch and pull requests
- reduce credential fallback paths between services
- move device provisioning and firmware updates toward a signed, production-safe lifecycle
