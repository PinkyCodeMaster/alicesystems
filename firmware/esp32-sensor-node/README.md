# esp32-sensor-node

- Purpose: MVP environmental and motion sensor firmware.
- Will contain: ESP-IDF application code for temperature, humidity, light, and motion sensing nodes.
- Responsibilities: Sample sensors, publish telemetry and retained state, and participate in secure provisioning and OTA.
- Interfaces: Uses shared firmware components plus sensor buses such as I2C and GPIO; communicates with Home OS over Wi-Fi and MQTT.
- Status: prototype.
