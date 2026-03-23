# mqtt-broker

- Purpose: Broker configuration and deployment assets for MQTT messaging.
- Will contain: Mosquitto configuration, local compose wiring, ACLs later, certificate assets later, and operational notes.
- Responsibilities: Provide reliable, local-first device messaging transport for Alice devices and local testing.
- Interfaces: Devices connect over MQTT; Home OS ingests `hello`, `availability`, `telemetry`, and `state` and publishes device commands.
- Status: in progress.

## Current State

Implemented now:

- local Mosquitto config in [mosquitto.conf](e:/alicesystems/infra/mosquitto/mosquitto.conf)
- Docker Compose service in [docker-compose.yml](e:/alicesystems/infra/docker/docker-compose.yml)
- PowerShell helpers in `infra/scripts`

Current local topic set:

- `alice/v1/device/{device_id}/hello`
- `alice/v1/device/{device_id}/availability`
- `alice/v1/device/{device_id}/telemetry`
- `alice/v1/device/{device_id}/state`
- `alice/v1/device/{device_id}/cmd`

Current status:

- prototype-safe local broker setup
- not yet production-safe
