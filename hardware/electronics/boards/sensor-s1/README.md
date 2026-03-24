# Sensor S1 (Prototype)

Status: prototype

## Purpose
First Alice Systems environmental sensor node.

## Features
- Temperature
- Humidity
- Light
- Motion (PIR)

## Hardware
- ESP32-S3 module
- BME280 or SHT31
- BH1750 or VEML7700
- PIR sensor input
- USB power

## Notes
- WiFi (MQTT)
- No battery yet
- Focus on reliability and simplicity

## Integration
- Publishes telemetry to Alice Home OS via MQTT
- Will be used for first real in-home testing

## Next Steps
- create KiCad schematic
- build prototype
- integrate with firmware