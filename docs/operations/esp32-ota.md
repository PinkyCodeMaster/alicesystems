# ESP32 OTA

## Purpose

This document covers the prototype-safe over-the-air update path for the current Arduino-based Alice ESP32 bench nodes.

## Status

- sensor node OTA: prototype
- relay node OTA: prototype
- signed Home OS managed OTA: planned

## Recommendation

Use USB for the first flash and recovery only. Use Wi-Fi OTA for day-to-day iteration while the boards are running in the house.

This is the correct short-term workflow because:

- it removes repeated unplugging and replugging
- it keeps serial available for bring-up when needed
- it avoids designing production OTA before the runtime is stable

## Current OTA Design

The current ESP32 prototype firmware uses Arduino OTA:

- transport: local Wi-Fi
- OTA port: `3232`
- hostname: `DEVICE_ID`
- password: optional, currently empty by default

Each board prints a line like this on boot:

```text
Arduino OTA ready on 192.168.0.28:3232
```

That IP is the OTA upload target.

## Sensor Node OTA

First flash by USB:

```powershell
cd E:\alicesystems\firmware\esp32-sensor-node
python -m platformio run -e esp32-sensor-node --target upload --upload-port COM5
```

Later updates by Wi-Fi:

```powershell
cd E:\alicesystems\firmware\esp32-sensor-node
python -m platformio run -e esp32-sensor-node-ota --target upload --upload-port <sensor-ip>
```

If mDNS works on your Windows machine:

```powershell
python -m platformio run -e esp32-sensor-node-ota --target upload --upload-port dev_sensor_hall_01.local
```

## Relay Node OTA

First flash by USB:

```powershell
cd E:\alicesystems\firmware\esp32-relay-node
python -m platformio run -e esp32-relay-node --target upload --upload-port COMX
```

Later updates by Wi-Fi:

```powershell
cd E:\alicesystems\firmware\esp32-relay-node
python -m platformio run -e esp32-relay-node-ota --target upload --upload-port <relay-ip>
```

If mDNS works on your Windows machine:

```powershell
python -m platformio run -e esp32-relay-node-ota --target upload --upload-port dev_light_bench_01.local
```

## Known Limits

- not signed
- not controlled by Home OS
- no staged rollout
- no rollback protection
- IP address can change unless the router reserves it

## Later Upgrade Path

The production Alice OTA path should be:

1. Home OS publishes firmware update intent
2. device downloads firmware from local Home OS over HTTPS
3. device verifies signature
4. device installs and reports result
5. Home OS records version and audit trail

That future path replaces prototype Arduino OTA; it does not extend it into production.
