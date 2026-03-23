# mosquitto

- Purpose: Broker-specific infrastructure configuration.
- Will contain: Mosquitto config, ACLs, retained-message policy notes, and TLS assets later.
- Responsibilities: Configure MQTT behavior to match Alice topic and auth rules.
- Interfaces: Supports `services/mqtt-broker` deployment and local device connectivity.
- Status: in progress.

## Current State

Implemented now:

- `mosquitto.conf` for local bench testing
- anonymous local listener on port `1883`

Current local setup is suitable for:

- development
- protocol testing
- first in-house ESP32 integration

It is not yet suitable for production-safe household deployment because device auth and broker ACLs are still pending.
