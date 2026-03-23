# esp32-relay-node

- Purpose: MVP relay or light control firmware.
- Will contain: ESP-IDF application code for relay control, command handling, acknowledgements, and safe boot behavior.
- Responsibilities: Execute authorized commands predictably and publish current state back to Home OS.
- Interfaces: Uses shared firmware components plus GPIO relay drivers; receives commands over MQTT and OTA over HTTPS.
- Status: prototype.
