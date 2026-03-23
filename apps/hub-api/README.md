# hub-api

- Purpose: Alice Home OS runtime and source of truth.
- Will contain: FastAPI application modules for auth, rooms, devices, entities, state, automations, policy, audit, provisioning, OTA, and assistant tool execution.
- Responsibilities: Own canonical state and enforce permissions, policy, and audit on all actions.
- Interfaces: REST and WebSocket for apps and assistant runtime; MQTT integration via internal services and workers.
- Status: in progress.
