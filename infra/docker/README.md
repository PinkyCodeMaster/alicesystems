# docker

- Purpose: Container deployment assets for Alice local infrastructure.
- Will contain: Compose definitions, service overrides, and container runtime notes.
- Responsibilities: Make the local-first stack easy to run and reproduce.
- Interfaces: Starts current local infrastructure such as Mosquitto and will later grow to include assistant and model runtimes.
- Status: in progress.

## Current State

Implemented now:

- `docker-compose.yml` with a local Mosquitto service
- `docker-compose.practice.yml` with a rehearsal stack for hub onboarding plus two mock claimable devices

Start command:

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
```

Practice stack:

```powershell
cd E:\alicesystems\infra\scripts
.\practice-up.ps1
```

That stack publishes:

- dashboard on `3000`
- hub API on `8000`
- assistant on `8010`
- mock sensor setup endpoint on `48081`
- mock relay setup endpoint on `48082`

See [practice/README.md](e:/alicesystems/infra/docker/practice/README.md) for the claim rehearsal flow.
