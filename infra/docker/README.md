# docker

- Purpose: Container deployment assets for Alice local infrastructure.
- Will contain: Compose definitions, service overrides, and container runtime notes.
- Responsibilities: Make the local-first stack easy to run and reproduce.
- Interfaces: Starts current local infrastructure such as Mosquitto and will later grow to include assistant and model runtimes.
- Status: in progress.

## Current State

Implemented now:

- `docker-compose.yml` with a local Mosquitto service

Start command:

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
```
