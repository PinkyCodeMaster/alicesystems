# esp32-sensor-node

- Purpose: Quick prototype firmware for the first real Alice sensor node using your current ESP32 dev board and bench sensors.
- Responsibilities: Connect to Wi-Fi, register with Home OS over MQTT, read DHT11 temperature, read the photoresistor on an ADC pin, read PIR motion, and publish retained state updates.
- Interfaces: Publishes to `alice/v1/device/{device_id}/hello`, `availability`, and `state` over MQTT.
- Status: prototype.

## Current Scope

This project is the fastest path to replacing fake MQTT publishes with a real board in your house.

Implemented in this prototype:

- Wi-Fi connection
- MQTT connection with retained `hello`
- retained `availability`
- retained `temperature`, `illuminance`, and `motion` state publishes
- immediate publish on motion edge
- immediate publish on temperature delta
- immediate publish on light delta
- on-board status LED state machine on `GPIO2`
- prototype Wi-Fi OTA after first USB flash
- simple reconnect loop

Not implemented yet:

- secure provisioning
- mTLS
- signed OTA
- flash encryption
- signed firmware
- deep sleep or battery optimisation

## Hardware Mapping

Current default pin map in [device_config.h](e:/alicesystems/firmware/esp32-sensor-node/include/device_config.h):

- light sensor analog out: `GPIO34`
- DHT11 data: `GPIO26`
- PIR output: `GPIO27`
- status LED: `GPIO2`

Important:

- `GPIO34` is input-only, which is correct for the light sensor ADC input.
- `GPIO27` is a sensible digital input choice for the PIR on a typical ESP32 dev board.
- `GPIO2` is used here only as a status LED on the sensor board.
- This project assumes a `DHT11`. If your module is different, adjust `DHT_TYPE` in code.

## Status LED Behaviour

Sensor board `GPIO2` now behaves like this:

- fast blink: board booting
- medium blink: connecting to Wi-Fi
- slow blink: connecting to MQTT and Home OS
- solid on: connected to Home OS
- off after two minutes: normal run state

This is intentionally only on the sensor board. The relay node uses `GPIO2` as the actual controlled light output, so overloading it for status would create unsafe and confusing behaviour.

## Folder Layout

- [platformio.ini](e:/alicesystems/firmware/esp32-sensor-node/platformio.ini): build config
- [device_config.h](e:/alicesystems/firmware/esp32-sensor-node/include/device_config.h): pins and publish timing
- [secrets.example.h](e:/alicesystems/firmware/esp32-sensor-node/include/secrets.example.h): copy to `secrets.h` and fill in Wi-Fi and MQTT
- [main.cpp](e:/alicesystems/firmware/esp32-sensor-node/src/main.cpp): prototype node logic

## Event-Driven Publish Behaviour

The node still publishes a full snapshot every `15s`, but it now also publishes immediately when:

- motion changes
- temperature changes by at least `0.3 C`
- light sensor raw ADC changes by at least `200`

Those thresholds are defined in [device_config.h](e:/alicesystems/firmware/esp32-sensor-node/include/device_config.h).

## Setup

1. Copy [secrets.example.h](e:/alicesystems/firmware/esp32-sensor-node/include/secrets.example.h) to `include/secrets.h`.
2. Fill in your local Wi-Fi and MQTT values.
3. Confirm the pin map in [device_config.h](e:/alicesystems/firmware/esp32-sensor-node/include/device_config.h).
4. Flash with PlatformIO.

## OTA Workflow

After the first USB flash, this node can be updated over Wi-Fi on your local network.

Default OTA settings:

- hostname: `DEVICE_ID`
- port: `3232`
- password: empty by default for prototype use only

Recommended Windows command after the board is already on Wi-Fi:

```powershell
cd E:\alicesystems\firmware\esp32-sensor-node
python -m platformio run -e esp32-sensor-node-ota --target upload --upload-port <sensor-ip>
```

If mDNS works on your machine, hostname upload is also acceptable:

```powershell
python -m platformio run -e esp32-sensor-node-ota --target upload --upload-port dev_sensor_hall_01.local
```

Watch serial once after first boot and note the line:

```text
Arduino OTA ready on 192.168.0.28:3232
```

That is the IP to use for later OTA uploads. If DHCP changes it later, use the new address from serial or your router.

## Expected MQTT Contract

Topics:

- `alice/v1/device/{device_id}/hello`
- `alice/v1/device/{device_id}/availability`
- `alice/v1/device/{device_id}/state`

Published state payload examples:

```json
{"capability":"temperature","celsius":21.7}
{"capability":"illuminance","lux":143.2,"raw":1876}
{"capability":"motion","motion":true}
```

## Flash Workflow

Recommended on Windows:

1. Install VS Code
2. Install the PlatformIO IDE extension
3. Open `E:\alicesystems`
4. Open this folder in PlatformIO
5. Build and upload the `esp32-sensor-node` environment
6. Open the serial monitor at `115200`

If you prefer CLI later, use PlatformIO CLI. This machine does not currently have `platformio` installed, so CLI build was not verified here.

For recovery or first flash, keep using USB:

```powershell
python -m platformio run -e esp32-sensor-node --target upload --upload-port COM5
```

## Safe Bench-Test Sequence

1. Start local Mosquitto.
2. Start `hub-api` with `MQTT_ENABLED=true`.
3. Power the board over USB only.
4. Verify `hello` creates the device in `/api/v1/devices`.
5. Watch `/api/v1/entities` for `temperature`, `illuminance`, and `motion`.
6. Trigger the PIR and cover/uncover the light sensor.
7. Confirm live state updates in the API before moving on.

## Known Gaps

- light sensor `lux` is an estimate derived from ADC input, not a calibrated lux reading
- DHT11 is slow and noisy
- no room assignment or provisioning yet
- no offline queueing

## Next Steps

- replace DHT11 with a better sensor in the production node
- move from bench secrets to proper provisioning
- port the proven logic into ESP-IDF runtime components
