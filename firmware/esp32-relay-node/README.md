# esp32-relay-node

- Purpose: Quick prototype firmware for the second ESP32 acting as the first Alice light or relay node.
- Responsibilities: Connect to Wi-Fi, register with Home OS over MQTT, listen for `switch.set` commands, drive GPIO2, and publish retained relay state.
- Interfaces: Publishes to `alice/v1/device/{device_id}/hello`, `availability`, and `state`, and subscribes to `alice/v1/device/{device_id}/cmd`.
- Status: prototype.

## Current Scope

Implemented in this prototype:

- Wi-Fi connection
- MQTT connection with retained `hello`
- retained `availability`
- retained relay state publish
- command subscription for `switch.set`
- explicit MQTT command acknowledgement on `ack`
- periodic relay state heartbeat publish
- safe default boot state of `off`
- prototype Wi-Fi OTA after first USB flash

Not implemented yet:

- secure provisioning
- signed OTA
- signed commands
- mTLS
- relay hardware protection circuits

## Hardware Mapping

Current default pin map in [device_config.h](e:/alicesystems/firmware/esp32-relay-node/include/device_config.h):

- LED or relay output: `GPIO2`
- active-high output logic

If your relay module is active-low, set `OUTPUT_ACTIVE_HIGH` to `false`.

## Folder Layout

- [platformio.ini](e:/alicesystems/firmware/esp32-relay-node/platformio.ini): build config
- [device_config.h](e:/alicesystems/firmware/esp32-relay-node/include/device_config.h): output pin and reconnect timing
- [secrets.example.h](e:/alicesystems/firmware/esp32-relay-node/include/secrets.example.h): copy to `secrets.h` and fill in Wi-Fi and MQTT
- [main.cpp](e:/alicesystems/firmware/esp32-relay-node/src/main.cpp): prototype node logic

## Expected MQTT Contract

Topics:

- `alice/v1/device/{device_id}/hello`
- `alice/v1/device/{device_id}/availability`
- `alice/v1/device/{device_id}/state`
- `alice/v1/device/{device_id}/ack`
- `alice/v1/device/{device_id}/cmd`

Accepted command shape:

```json
{
  "type": "entity.command",
  "name": "switch.set",
  "params": {
    "on": true
  }
}
```

Published state shape:

```json
{"capability":"relay","on":true}
```

Published ack shape:

```json
{
  "cmd_id": "cmd_...",
  "target_entity_id": "ent_dev_light_bench_01_relay",
  "status": "applied",
  "name": "switch.set",
  "params": {"on": true},
  "state": {"on": true}
}
```

## OTA Workflow

After the first USB flash, this node can be updated over Wi-Fi on your local network.

Default OTA settings:

- hostname: `DEVICE_ID`
- port: `3232`
- password: empty by default for prototype use only

Recommended Windows command after the board is already on Wi-Fi:

```powershell
cd E:\alicesystems\firmware\esp32-relay-node
python -m platformio run -e esp32-relay-node-ota --target upload --upload-port <relay-ip>
```

If mDNS works on your machine, hostname upload is also acceptable:

```powershell
python -m platformio run -e esp32-relay-node-ota --target upload --upload-port dev_light_bench_01.local
```

Watch serial once after first boot and note the line:

```text
Arduino OTA ready on 192.168.0.X:3232
```

That is the IP to use for later OTA uploads. If DHCP changes it later, use the new address from serial or your router.

## Flash Workflow

Recommended on Windows:

1. Install VS Code
2. Install the PlatformIO IDE extension
3. Open `E:\alicesystems`
4. Open this folder in PlatformIO
5. Build and upload the `esp32-relay-node` environment
6. Open the serial monitor at `115200`

This machine does not currently have PlatformIO CLI installed, so CLI build was not verified here.

For recovery or first flash, keep using USB:

```powershell
python -m platformio run -e esp32-relay-node --target upload --upload-port COMX
```

## Safe Bench-Test Sequence

1. Start local Mosquitto.
2. Start `hub-api` with `MQTT_ENABLED=true`.
3. Flash this board and power it over USB only.
4. Confirm the node appears in `/api/v1/devices`.
5. Confirm the writable relay entity appears in `/api/v1/entities`.
6. Use Scalar or Swagger to call `POST /api/v1/entities/{entity_id}/commands`.
7. Verify GPIO2 changes state and the board publishes updated relay state.

## Known Gaps

- this is a bench-safe LED output only, not yet a mains-rated smart switch design
- no command acknowledgement message yet
- no hardware watchdog or failsafe relay driver yet

## Next Steps

- replace LED with a transistor or relay driver stage
- add state reconciliation and command ack
- move the proven logic into the hardened ESP-IDF runtime
