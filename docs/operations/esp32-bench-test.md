# ESP32 Bench Test

## Purpose

This document is the fastest bench-test path for replacing fake MQTT publishes with the two real ESP32 boards already on hand.

## Status

- sensor node firmware: prototype
- relay node firmware: prototype
- hub MQTT ingest: in progress and locally verified
- live two-board house test: next step

## Hardware Under Test

Board 1:

- ESP32 sensor node
- DHT11 on `GPIO26`
- light sensor analog output on `GPIO34`
- PIR on `GPIO27`
- status LED on `GPIO2`

Board 2:

- ESP32 light node
- LED on `GPIO2`

## Important Wiring Note

If the PIR never changes state, check the module power, ground, and output polarity, then confirm the configured pin in:

- [device_config.h](e:/alicesystems/firmware/esp32-sensor-node/include/device_config.h)

## Before Flashing

1. Start Mosquitto:

```powershell
cd E:\alicesystems\infra\scripts
.\mqtt-up.ps1
```

2. Start `hub-api` with MQTT enabled:

```powershell
cd E:\alicesystems\apps\hub-api
.\.alice\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

3. Confirm `E:\alicesystems\apps\hub-api\.env` contains:

```env
MQTT_ENABLED=true
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=alice/v1
```

## Sensor Node Setup

1. Copy:
   [secrets.example.h](e:/alicesystems/firmware/esp32-sensor-node/include/secrets.example.h)
   to `firmware/esp32-sensor-node/include/secrets.h`
2. Set Wi-Fi and MQTT host.
3. Set `DEVICE_ID` to the real board ID you want to keep.
4. Flash the project in:
   [esp32-sensor-node](e:/alicesystems/firmware/esp32-sensor-node)

## Relay Node Setup

1. Copy:
   [secrets.example.h](e:/alicesystems/firmware/esp32-relay-node/include/secrets.example.h)
   to `firmware/esp32-relay-node/include/secrets.h`
2. Set Wi-Fi and MQTT host.
3. Set `DEVICE_ID` to the real board ID you want to keep.
4. Flash the project in:
   [esp32-relay-node](e:/alicesystems/firmware/esp32-relay-node)

## What To Verify

1. `GET /api/v1/devices`
   - sensor node appears online
   - relay node appears online
2. `GET /api/v1/entities`
   - sensor node has `temperature`, `illuminance`, and `motion`
   - relay node has writable `relay`
3. `GET /api/v1/entities/{temperature_entity_id}/state`
   - temperature updates
4. `GET /api/v1/entities/{motion_entity_id}/state`
   - motion changes when PIR triggers
5. `POST /api/v1/entities/{relay_entity_id}/commands`
   - LED on GPIO2 changes

## Optional Prototype Auto-Light Rule

For the current two-board bench setup, the safe place for lux-based light control is Home OS, not direct ESP32-to-ESP32 logic.

Add these values to `E:\alicesystems\apps\hub-api\.env` after the real entities exist:

```env
AUTO_LIGHT_ENABLED=true
AUTO_LIGHT_SENSOR_ENTITY_ID=ent_dev_sensor_hall_01_illuminance
AUTO_LIGHT_TARGET_ENTITY_ID=ent_dev_light_bench_01_relay
AUTO_LIGHT_MODE=raw_high_turn_on
AUTO_LIGHT_ON_RAW=3000
AUTO_LIGHT_OFF_RAW=2600
```

Then restart `hub-api`.

Behavior:

- if sensor `raw` is `>= 3000`, Home OS commands the light on
- if sensor `raw` is `<= 2600`, Home OS commands the light off
- values between those thresholds do nothing, which prevents rapid chattering

## Command Body For Relay Test

```json
{
  "command": "switch.set",
  "params": {
    "on": true
  }
}
```

## OTA Prototype Workflow

After each board has been flashed once over USB, you can update them over Wi-Fi instead of unplugging them.

Sensor board:

```powershell
cd E:\alicesystems\firmware\esp32-sensor-node
python -m platformio run -e esp32-sensor-node-ota --target upload --upload-port <sensor-ip>
```

Relay board:

```powershell
cd E:\alicesystems\firmware\esp32-relay-node
python -m platformio run -e esp32-relay-node-ota --target upload --upload-port <relay-ip>
```

Notes:

- first flash still needs USB
- OTA target IP can change if your router changes leases
- watch serial once and note the `Arduino OTA ready on ...` line
- this is prototype-safe only, not production-safe signed OTA

## Current Limits

- no provisioning flow
- no device authentication
- no encrypted MQTT
- not suitable for mains switching without proper output hardware
