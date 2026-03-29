# ESP32 Provisioning Transition

## Purpose

This document defines how the two current ESP32 prototype boards should evolve from hardcoded bench nodes into claimable Alice devices.

It is intentionally narrow:

- current boards: `dev_sensor_hall_01` and `dev_light_bench_01`
- current transport: Wi-Fi + MQTT
- current control plane: local `hub-api`
- next product goal: first real owner onboarding and device claim flow

## Current State

Today the boards are bench prototypes, not consumer devices.

Current assumptions:

- Wi-Fi credentials are compiled into `secrets.h`
- MQTT broker host is compiled into `secrets.h`
- device identity is compiled into `secrets.h`
- the hub discovers devices from retained MQTT `hello`
- there is no claim handshake
- there is no device-side proof of ownership
- there is no printed setup code or QR bootstrap payload

Current board identities in this repo:

- sensor: `dev_sensor_hall_01`
- relay: `dev_light_bench_01`

This is sufficient for bench validation but not for real onboarding.

## What Must Change

The next firmware iteration should remove only the parts that block onboarding, while keeping the proven MQTT capability contract.

Keep:

- MQTT `hello`
- MQTT `availability`
- MQTT `state`
- MQTT `cmd`
- MQTT `ack`
- current capability descriptors and entity shapes
- current sensor and relay business logic

Replace:

- hardcoded Wi-Fi credentials
- hardcoded MQTT host
- hardcoded final device identity as the only identity
- direct boot into normal operating mode

Add:

- bootstrap identity
- claimable setup state
- QR / printed code metadata
- provisioning handshake with Home OS
- persisted claimed credentials

## Firmware Modes

The device runtime should have three explicit modes.

### 1. Factory / Unclaimed

The device has:

- immutable hardware serial or generated bootstrap ID
- model and hardware revision
- bootstrap secret or key material
- no final site ownership
- no final MQTT credentials
- no room assignment

Behavior:

- does not publish normal MQTT `hello/state` to the production topic path
- exposes a short-range setup channel for claim bootstrap
- advertises itself as claimable
- can prove it is the physical device described by its QR or setup code

### 2. Claiming

The device receives:

- local Wi-Fi credentials
- hub address
- short-lived claim token

Behavior:

- connects to the target network
- exchanges bootstrap proof with Home OS
- receives final device identity and MQTT credentials
- persists claimed configuration

### 3. Claimed / Normal Runtime

Behavior:

- connects with claimed credentials
- publishes retained MQTT `hello`
- publishes `availability`
- publishes `state`
- listens for `cmd`
- publishes `ack`

This mode should look as close as possible to the current working prototype behavior.

## Recommended Identity Model

Separate bootstrap identity from operational identity.

Bootstrap identity:

- `bootstrap_id`
- `model`
- `hardware_revision`
- `bootstrap_secret` or device keypair

Operational identity:

- `device_id`
- `site_id`
- `mqtt_client_id`
- MQTT username/password or client cert

Rule:

- the QR and printed code should identify the bootstrap identity, not just the final MQTT runtime identity

## QR And Setup Code

Do not put raw long-lived secrets directly into a printed QR.

Recommended payload:

```json
{
  "v": 1,
  "bootstrap_id": "boot_sensor_7Q2K9M",
  "model": "alice.sensor.env.s1",
  "setup_code": "482913",
  "claim_url": "https://hub.local/api/v1/provisioning"
}
```

Rules:

- `setup_code` should be short enough to type manually
- QR should speed up onboarding, not replace verification
- Home OS must still verify the device using bootstrap proof

## Recommended Claim Handshake

This is the narrowest path that fits the current stack.

### Step 1. User starts claim

Mobile app:

- scans QR or accepts manual setup code
- calls Home OS to create a provisioning session

Home OS returns:

- `provisioning_session_id`
- short-lived `claim_token`
- target hub address

### Step 2. App transfers bootstrap inputs to device

For the current ESP32 generation, use temporary local AP mode as the simplest path.

Device in unclaimed mode:

- exposes temporary setup AP
- serves small local setup page or simple local API

Mobile app sends:

- Wi-Fi SSID/password
- hub address
- claim token

### Step 3. Device proves bootstrap identity to Home OS

Device calls Home OS provisioning endpoint with:

- `bootstrap_id`
- setup code or signed bootstrap proof
- `claim_token`
- model metadata

Home OS validates:

- provisioning session is open
- bootstrap proof matches known manufacturing record
- device is not already claimed, or recovery policy allows reset

### Step 4. Home OS issues final runtime config

Home OS returns:

- `device_id`
- `mqtt_client_id`
- MQTT credentials
- MQTT host/port/topic prefix
- optional room/name defaults

### Step 5. Device reboots into normal mode

Device persists final config and then:

- disables setup AP
- reconnects using final credentials
- publishes normal MQTT `hello`

## What The Two Current Boards Need

The sensor and relay boards do not need a capability rewrite first.

They do need these firmware changes:

1. Move `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_HOST`, and final operational identity out of required compile-time secrets.
2. Add a small persisted config store in flash for claimed runtime settings.
3. Add unclaimed boot mode and temporary setup AP.
4. Add a provisioning client that can exchange bootstrap proof for runtime credentials.
5. Keep the current MQTT runtime path after claim.

They do not yet need:

- Matter
- cloud dependency
- complex mesh logic
- assistant integration

## Minimal Data Model Needed In Home OS

The current `devices` table already has `provisioning_status`, but that is not enough.

The next backend slice should add records for:

- `device_bootstrap_records`
- `provisioning_sessions`
- `device_credentials`

Suggested responsibilities:

- `device_bootstrap_records`: factory-known bootstrap IDs, setup codes, model, status
- `provisioning_sessions`: who is claiming, session expiry, current step, target site
- `device_credentials`: issued runtime MQTT credentials or cert references

## Migration Path For The Two Existing Boards

Use these phases.

### Phase 0. Keep Bench Pair Stable

Do now:

- keep `dev_sensor_hall_01` and `dev_light_bench_01` running the existing prototype
- stop changing IDs unless absolutely necessary
- use them to validate hub, UI, automations, and assistant tool paths

### Phase 1. Add Claim-Capable Firmware Branch

Do next:

- branch the current firmware runtime
- preserve sensor and relay logic
- add unclaimed mode and persisted config

This should still be testable on the same two boards.

### Phase 2. Add Home OS Claim API

Do after the firmware branch exists:

- create provisioning session routes
- issue claim tokens
- verify bootstrap proof
- issue runtime MQTT credentials

### Phase 3. Add Mobile Onboarding UI

Do after backend claim routes exist:

- scan QR
- manual setup code fallback
- transfer Wi-Fi credentials to device AP
- assign name and room

### Phase 4. Retire Hardcoded `secrets.h`

Only after claim flow works:

- keep only bootstrap constants in firmware
- stop compiling final Wi-Fi and MQTT settings into the firmware image

## Non-Goals For This Slice

Do not expand scope with these yet:

- signed production OTA
- mTLS everywhere
- manufacturing line software
- multi-hub roaming
- advanced recovery/reset UX

Those matter, but they are not the blocking step between today's prototype and first usable onboarding.

## Definition Of Done

This slice is done when:

1. a brand new ESP32 boots unclaimed
2. a user can scan its QR in mobile
3. the app sends Wi-Fi and claim inputs to the device
4. the device proves identity to Home OS
5. Home OS issues final runtime config
6. the device reboots and appears in Alice normally
7. the user names it and assigns it to a room

At that point, the current bench architecture becomes a real product path instead of a developer-only path.
