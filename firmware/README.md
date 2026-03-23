# firmware

- Purpose: Device-side runtime code for Alice hardware.
- Will contain: Shared ESP-IDF components, device apps, network stacks, OTA logic, and future product firmware lines.
- Responsibilities: Run device capabilities reliably and securely while staying subordinate to Home OS authority.
- Interfaces: MQTT for state and commands, HTTPS for provisioning and OTA, local sensors and actuators on hardware.
- Status: in progress.
