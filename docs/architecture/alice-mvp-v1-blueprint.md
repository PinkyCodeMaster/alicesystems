# Alice Systems MVP v1 Blueprint

## A. Recommendation

Build Alice MVP v1 as a local-first platform with three explicit runtimes:

1. `Alice Home OS`
2. `Alice Assistant Runtime`
3. `Alice Device Runtime`

Use a future-proof monorepo from day one, but keep the MVP execution path narrow:

- Home OS: FastAPI modular monolith + SQLite + MQTT + worker
- Assistant: separate local service using Ollama, Whisper-class STT, and Piper
- Devices: ESP-IDF firmware on ESP32, using Wi-Fi + MQTT now and HTTPS for provisioning/OTA

Make the repo broad enough for the company roadmap, but make only a small subset active now.

## B. Why

This is the right shape because it protects long-term platform ownership without forcing premature complexity.

- A modular monolith is faster to build and easier to reason about than microservices for a solo founder.
- A separate assistant runtime preserves the security rule that AI is not authoritative.
- Wi-Fi + MQTT on ESP32 gets you to working product loops fastest for mains-powered hardware.
- SQLite is sufficient for single-hub MVP deployments and keeps local setup simple.
- A structured monorepo prevents the project from becoming a prototype repo that later needs painful reorganization.

### Alternatives Considered

| Option | Decision | Why Not Chosen |
|---|---|---|
| Microservices from day one | Reject | Too much orchestration and operational drag for MVP. |
| Assistant embedded inside Home OS | Reject | Weakens policy and audit boundaries. |
| Zigbee/Thread-first for all devices | Defer | Correct later for battery and mesh, but slower for MVP delivery. |
| Cloud-managed control plane | Reject | Violates local-first and privacy-first goals. |
| Home Assistant-based architecture | Reject | Violates product independence requirement. |

## C. Architecture

## 1. Top-Level System Architecture

```text
Clients
  mobile-app (Expo)
  web-dashboard (Next.js)
  future wall-panel-ui / tv-interface / wearable-interface / car-integration
        |
        | REST + WebSocket
        v
Alice Home OS
  hub-api (FastAPI modular monolith)
  automation-worker
  SQLite canonical store
  policy, audit, provisioning, OTA, automations
        |
        | MQTT command/state plane
        v
Mosquitto
        |
        +--> esp32-sensor-node
        +--> esp32-relay-node
        +--> future Thread/Matter and other product lines via bridges or native runtime

Alice Assistant Runtime
  STT -> LLM/tool calling -> TTS
        |
        | authenticated tool API only
        v
Alice Home OS
```

### Architectural Rules

- Home OS is the only authority for users, rooms, devices, entities, automations, permissions, audit, and canonical state.
- Devices expose typed capabilities, not user-specific behavior.
- Assistant never talks directly to devices or MQTT.
- Bridges for Matter, Thread, cameras, and other ecosystems are adapters, not core architecture.

## 2. Future-Proof Monorepo Structure

### Full Folder Tree

```text
alicesystems/
├─ README.md
├─ .github/
│  └─ workflows/
├─ apps/
│  ├─ README.md
│  ├─ hub-api/
│  │  └─ README.md
│  ├─ assistant-runtime/
│  │  └─ README.md
│  ├─ web-dashboard/
│  │  └─ README.md
│  ├─ mobile-app/
│  │  └─ README.md
│  ├─ wall-panel-ui/
│  │  └─ README.md
│  ├─ tv-interface/
│  │  └─ README.md
│  ├─ wearable-interface/
│  │  └─ README.md
│  └─ car-integration/
│     └─ README.md
├─ packages/
│  ├─ README.md
│  ├─ contracts/
│  │  └─ README.md
│  ├─ common-py/
│  │  └─ README.md
│  ├─ common-ts/
│  │  └─ README.md
│  ├─ device-capabilities/
│  │  └─ README.md
│  ├─ ui-web/
│  │  └─ README.md
│  ├─ ui-mobile/
│  │  └─ README.md
│  └─ voice-assets/
│     └─ README.md
├─ services/
│  ├─ README.md
│  ├─ mqtt-broker/
│  │  └─ README.md
│  ├─ automation-worker/
│  │  └─ README.md
│  ├─ media-gateway/
│  │  └─ README.md
│  ├─ camera-stack/
│  │  └─ README.md
│  ├─ matter-bridge/
│  │  └─ README.md
│  ├─ thread-border-router/
│  │  └─ README.md
│  └─ router-control-plane/
│     └─ README.md
├─ firmware/
│  ├─ README.md
│  ├─ alice-common/
│  │  └─ README.md
│  ├─ esp32-sensor-node/
│  │  └─ README.md
│  ├─ esp32-relay-node/
│  │  └─ README.md
│  ├─ esp32-wall-panel/
│  │  └─ README.md
│  ├─ thread-matter/
│  │  └─ README.md
│  ├─ router-ap-firmware/
│  │  └─ README.md
│  └─ wearable-firmware/
│     └─ README.md
├─ hardware/
│  ├─ README.md
│  ├─ product-families/
│  │  ├─ README.md
│  │  ├─ hub-h1/
│  │  │  └─ README.md
│  │  ├─ sensor-s1/
│  │  │  └─ README.md
│  │  ├─ relay-r1/
│  │  │  └─ README.md
│  │  ├─ plug-p1/
│  │  │  └─ README.md
│  │  ├─ wall-panel-w1/
│  │  │  └─ README.md
│  │  ├─ presence-radar-p1/
│  │  │  └─ README.md
│  │  ├─ camera-c1/
│  │  │  └─ README.md
│  │  ├─ router-ap-r1/
│  │  │  └─ README.md
│  │  ├─ wearable-w1/
│  │  │  └─ README.md
│  │  ├─ car-adapter-c1/
│  │  │  └─ README.md
│  │  └─ phone-p1/
│  │     └─ README.md
│  ├─ electronics/
│  │  └─ README.md
│  └─ mechanical/
│     └─ README.md
├─ manufacturing/
│  ├─ README.md
│  ├─ fixtures/
│  │  └─ README.md
│  ├─ programming-jigs/
│  │  └─ README.md
│  ├─ test-procedures/
│  │  └─ README.md
│  └─ boms/
│     └─ README.md
├─ compliance/
│  ├─ README.md
│  ├─ ukca/
│  │  └─ README.md
│  ├─ ce/
│  │  └─ README.md
│  ├─ emc/
│  │  └─ README.md
│  ├─ safety/
│  │  └─ README.md
│  └─ radio/
│     └─ README.md
├─ docs/
│  ├─ README.md
│  ├─ architecture/
│  │  ├─ README.md
│  │  └─ alice-mvp-v1-blueprint.md
│  ├─ api/
│  │  └─ README.md
│  ├─ device/
│  │  └─ README.md
│  ├─ security/
│  │  └─ README.md
│  ├─ product/
│  │  └─ README.md
│  ├─ ux/
│  │  └─ README.md
│  └─ operations/
│     └─ README.md
├─ infra/
│  ├─ README.md
│  ├─ docker/
│  │  └─ README.md
│  ├─ mosquitto/
│  │  └─ README.md
│  ├─ scripts/
│  │  └─ README.md
│  └─ provisioning/
│     └─ README.md
├─ ml/
│  ├─ README.md
│  ├─ models/
│  │  └─ README.md
│  ├─ fine-tuning/
│  │  └─ README.md
│  ├─ evaluation/
│  │  └─ README.md
│  ├─ datasets/
│  │  └─ README.md
│  └─ voice/
│     └─ README.md
└─ tools/
   ├─ README.md
   ├─ dev/
   │  └─ README.md
   ├─ build/
   │  └─ README.md
   ├─ qa/
   │  └─ README.md
   └─ manufacturing/
      └─ README.md
```

### Active Now

| Folder | Status | Why Active |
|---|---|---|
| `apps/hub-api` | in progress | Home OS core runtime |
| `apps/assistant-runtime` | in progress | local assistant orchestration |
| `apps/web-dashboard` | in progress | browser control/admin |
| `apps/mobile-app` | in progress | onboarding and daily control |
| `packages/contracts` | in progress | shared schemas and IDs |
| `packages/device-capabilities` | in progress | capability model |
| `services/mqtt-broker` | in progress | MQTT transport |
| `services/automation-worker` | planned for MVP | background jobs and rule execution |
| `firmware/alice-common` | in progress | shared ESP-IDF components |
| `firmware/esp32-sensor-node` | prototype | sensor node |
| `firmware/esp32-relay-node` | prototype | relay/light node |
| `hardware/product-families/sensor-s1` | prototype | first sensor hardware |
| `hardware/product-families/relay-r1` | prototype | first actuator hardware |
| `docs/architecture` | in progress | design decisions |
| `infra/docker` | planned for MVP | local deployment |
| `infra/mosquitto` | planned for MVP | broker config |
| `infra/scripts` | planned for MVP | bring-up scripts |

### Placeholders

All other folders in the tree are intentional placeholders. Each already has a `README.md` that defines:

- purpose
- future contents
- responsibilities
- expected interfaces
- current status

This keeps future platform lines explicit instead of implicit.

## 3. Hub Runtime Services

### Recommended MVP Deployment Units

| Unit | Technology | Responsibility |
|---|---|---|
| `hub-api` | FastAPI | auth, registry, state, commands, automations, audit, provisioning, OTA, assistant tools |
| `automation-worker` | Python process | async jobs, automation execution, retries, OTA orchestration |
| `mosquitto` | Mosquitto | device messaging transport |
| `sqlite` | SQLite WAL | canonical local database |
| `assistant-runtime` | Python service | STT, LLM orchestration, tool calling, TTS |
| `ollama` | local service | model inference |

### Home OS Ownership

Home OS owns:

- users
- rooms
- devices
- entities
- state
- automations
- permissions
- audit logs
- provisioning
- OTA records
- notifications
- tool execution policy

## 4. Device Runtime Architecture

### Firmware Baseline

- `ESP-IDF` for all production-intended Espressif targets
- `ESP32-S3` for richer sensor or interface nodes
- `ESP32-C3` for lower-cost Wi-Fi actuator nodes
- HTTPS for provisioning and OTA
- MQTT for telemetry, retained state, commands, and availability

### Shared Firmware Layers

| Layer | Purpose |
|---|---|
| `board_support` | GPIO, I2C, ADC, relay, LEDs |
| `alice_storage` | NVS config and secrets |
| `alice_crypto` | signature and key helpers |
| `alice_net` | Wi-Fi setup and reconnection |
| `alice_mqtt` | MQTT client and publish/subscribe envelope handling |
| `alice_ota` | signed manifest fetch, image verification, rollback |
| `alice_capabilities` | capability-specific handlers |
| `alice_app` | node-specific task orchestration |

### Sensor Node MVP

Capabilities:

- `sensor.temperature`
- `sensor.humidity`
- `sensor.illuminance`
- `sensor.motion`

Recommended BOM direction:

- ESP32-S3 module
- BME280 or SHT31
- BH1750 or VEML7700
- Panasonic EKMB or similar PIR

### Relay / Light Node MVP

Capabilities:

- `switch.relay`
- optional `light.basic`

Rules:

- safe default boot state
- explicit state acknowledgement
- local override input optional
- no autonomous user-facing logic on device

## 5. Assistant Runtime Architecture

### Modules

| Module | Purpose |
|---|---|
| `sessions` | conversation lifecycle |
| `stt` | Whisper/faster-whisper integration |
| `llm` | prompt and tool orchestration with Ollama |
| `tools` | Home OS API client only |
| `memory` | optional structured and semantic recall |
| `tts` | Piper synthesis |
| `orchestrator` | end-to-end turn management |

### Hard Boundary

Assistant may:

- read state through Home OS
- ask for tool execution
- explain state and results

Assistant may not:

- publish MQTT
- call devices directly
- bypass policy
- silently execute unsafe actions

## 6. API Boundaries

### App to Home OS

- `REST` for CRUD, commands, provisioning, OTA admin, auth
- `WebSocket` for live entity state, audit, and notifications

### Device to Home OS

- `MQTT` for telemetry, availability, retained state, commands, acks
- `HTTPS` for provisioning bootstrap and OTA artifact retrieval

### Assistant to Home OS

- `REST` for context fetch and tool execution
- optional `WebSocket` for live conversation context later

### Home OS Internal Modules

- `auth`
- `users`
- `rooms`
- `devices`
- `entities`
- `state`
- `automations`
- `policy`
- `audit`
- `provisioning`
- `ota`
- `assistant_tools`

## 7. MQTT Topic Namespace

Use versioned topics from day one.

| Topic | Direction | Retained | Purpose |
|---|---|---|---|
| `alice/v1/device/{device_id}/hello` | device -> hub | no | boot announce |
| `alice/v1/device/{device_id}/availability` | device -> hub | yes | `online` / `offline` via LWT |
| `alice/v1/device/{device_id}/telemetry` | device -> hub | no | sensor or runtime readings |
| `alice/v1/device/{device_id}/state` | device -> hub | yes | latest local state |
| `alice/v1/device/{device_id}/event` | device -> hub | no | boot, fault, tamper, local input |
| `alice/v1/device/{device_id}/ack` | device -> hub | no | command acknowledgement |
| `alice/v1/device/{device_id}/cmd` | hub -> device | no | command envelope |
| `alice/v1/device/{device_id}/config` | hub -> device | yes | effective runtime config |
| `alice/v1/site/{site_id}/broadcast` | hub -> devices | no | controlled broadcast events |

### Envelope Example

```json
{
  "msg_id": "01HZX8K6FYQ6N8M0A1JQK4AN4W",
  "ts": "2026-03-23T10:15:21Z",
  "schema": "alice.device.telemetry.v1",
  "device_id": "dev_01HQ2J0N7RZ5Y7D3M3AWJ7S2Q8",
  "fw_version": "0.1.0",
  "body": {
    "capability": "sensor.temperature",
    "celsius": 21.4
  }
}
```

## 8. Device Capability Descriptor Schema

### Design Rule

Capabilities are declarative and typed. Home OS maps capabilities to entities.

### Example

```json
{
  "schema_version": "1.0",
  "device_model": "alice.sensor.env.s1",
  "capabilities": [
    {
      "id": "temperature",
      "kind": "sensor.temperature",
      "version": 1,
      "state_fields": [
        {"name": "last_celsius", "type": "float", "unit": "C"},
        {"name": "updated_at", "type": "datetime"}
      ],
      "telemetry_fields": [
        {"name": "celsius", "type": "float", "unit": "C"}
      ],
      "commands": []
    },
    {
      "id": "relay",
      "kind": "switch.relay",
      "version": 1,
      "state_fields": [
        {"name": "on", "type": "bool"},
        {"name": "updated_at", "type": "datetime"}
      ],
      "telemetry_fields": [],
      "commands": [
        {
          "name": "switch.set",
          "params": [
            {"name": "on", "type": "bool", "required": true}
          ]
        }
      ]
    }
  ]
}
```

## 9. Canonical Data Model

### Core Objects

| Object | Description |
|---|---|
| `site` | a single home installation |
| `user` | a Home OS identity |
| `room` | physical area |
| `device` | physical hardware endpoint |
| `entity` | user-visible, addressable object derived from a capability |
| `entity_state` | canonical latest state |
| `automation` | trigger/condition/action rule |
| `tool_action` | assistant or app action request and result |
| `audit_event` | immutable log record |

### Mapping Rule

- one device may expose multiple capabilities
- each capability usually maps to one primary entity
- entities are what apps, automations, and assistant tools address

## 10. SQLite Schema for MVP

Use SQLite with WAL mode.

### Required Tables

- `sites`
- `users`
- `rooms`
- `devices`
- `device_secrets`
- `entities`
- `entity_state`
- `entity_state_history`
- `automations`
- `tool_actions`
- `audit_events`
- `provisioning_sessions`
- `ota_artifacts`
- `ota_jobs`

### Minimal DDL Shape

```sql
CREATE TABLE devices (
  id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL,
  room_id TEXT,
  name TEXT NOT NULL,
  model TEXT NOT NULL,
  device_type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  status TEXT NOT NULL,
  provisioning_status TEXT NOT NULL,
  fw_version TEXT,
  mqtt_client_id TEXT NOT NULL UNIQUE,
  capability_descriptor_json TEXT NOT NULL,
  last_seen_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE entities (
  id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL,
  room_id TEXT,
  device_id TEXT NOT NULL,
  capability_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  writable INTEGER NOT NULL DEFAULT 0,
  traits_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE entity_state (
  entity_id TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  source TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);
```

The full table set is the minimum viable canonical store. Do not collapse state and audit into ad hoc blobs.

## 11. FastAPI Service / Module Breakdown

### Package Shape

```text
apps/hub-api/app/
  main.py
  core/
  api/routers/
  domain/
  schemas/
  repositories/
  services/
  workers/
```

### Router Surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/login` | login |
| `GET` | `/me` | current user |
| `GET` | `/rooms` | list rooms |
| `POST` | `/rooms` | create room |
| `GET` | `/devices` | list devices |
| `POST` | `/devices/register` | complete provisioning |
| `PATCH` | `/devices/{id}` | metadata updates |
| `GET` | `/entities` | list entities |
| `GET` | `/entities/{id}` | entity detail |
| `POST` | `/entities/{id}/commands` | app-driven command |
| `GET` | `/automations` | list automations |
| `POST` | `/automations` | create automation |
| `GET` | `/audit-events` | audit feed |
| `POST` | `/provisioning/sessions` | start claim session |
| `POST` | `/assistant/tools/execute` | assistant tool gateway |
| `GET` | `/assistant/context/home-summary` | compact context |
| `GET` | `/ws` | live event stream |

## 12. Expo Mobile App Screen Map

| Screen | Purpose |
|---|---|
| `Splash/Auth` | server selection and login |
| `Home` | home summary and quick actions |
| `RoomsList` | room navigation |
| `RoomDetail` | grouped devices/entities and controls |
| `DevicesList` | inventory and status |
| `DeviceDetail` | metadata, diagnostics, firmware |
| `Assistant` | text plus push-to-talk |
| `Automations` | list and create simple rules |
| `Activity` | audit and notifications |
| `Settings` | account, server, voice preferences |

## 13. Basic Web Dashboard Structure

| Screen | Purpose |
|---|---|
| `Login` | local auth |
| `Overview` | rooms, online devices, alerts |
| `Rooms` | room-centric monitoring and control |
| `Devices` | inventory, room assignment, firmware |
| `Entities` | canonical entity view |
| `Automations` | rule CRUD |
| `Audit` | security and action log |
| `Provisioning` | claim pending devices |
| `Settings` | site and runtime configuration |

## 14. Voice Pipeline Design

### MVP Voice Modes

| Mode | Support |
|---|---|
| Mobile push-to-talk | yes |
| Web push-to-talk | yes |
| Always-on wake word | no |
| Distributed microphones | no |

### Flow

1. capture audio from mobile or web
2. send or stream to assistant runtime
3. transcribe with Whisper-class STT
4. fetch compact context from Home OS
5. call LLM with tool schemas
6. if action needed, call Home OS tool gateway
7. generate response
8. synthesize with Piper
9. return audio/text to client

## 15. LLM Tool Calling Flow

### Initial Tool Set

| Tool | Purpose |
|---|---|
| `get_home_summary` | concise home context |
| `search_entities` | resolve likely targets |
| `get_entity_state` | inspect current state |
| `execute_entity_command` | request a writable action |
| `list_automations` | inspect automations |

### Tool Gateway Request Example

```json
{
  "assistant_session_id": "asst_01HQ2J9Y8QY5JMX6RNM7QW6F10",
  "user_id": "usr_founder",
  "tool_name": "execute_entity_command",
  "arguments": {
    "entity_id": "ent_hall_light_switch",
    "command": "switch.set",
    "params": {"on": true}
  }
}
```

### Hard Safety Rule

Every assistant action must become a Home OS `tool_action` record with:

- requester identity
- policy decision
- execution result
- audit correlation

## 16. Security Controls for MVP

### Mandatory

| Area | Control |
|---|---|
| Device identity | unique device ID and unique bootstrap secret |
| Provisioning | short-lived claim session and token verification |
| Messaging | authenticated MQTT credentials per device |
| Firmware integrity | signed OTA manifest and binary hash verification |
| Storage | encrypted secret storage on hub; encrypted device storage where practical |
| Policy | role-based checks in Home OS |
| Audit | immutable audit events for auth, claims, commands, OTA |
| AI control | tool-gated assistant only |

### Production-Hardening Path

- ESP secure boot
- flash encryption
- mTLS device auth
- secure element on higher-value devices
- formal threat reviews per product family

## 17. ESP32 Firmware Architecture for MVP Nodes

### Sensor Node

Main tasks:

- boot self-test
- load config from NVS
- connect Wi-Fi and MQTT
- publish `hello` and retained availability
- sample sensors on schedule
- debounce and publish motion events
- publish retained state summary
- check OTA manifest

### Relay Node

Main tasks:

- safe GPIO init
- load config and last safe state rules
- connect Wi-Fi and MQTT
- subscribe to `cmd`
- validate and execute relay commands
- publish ack and retained state
- expose local fault and restart events
- check OTA manifest

## 18. Provisioning and OTA Design for MVP

### Provisioning

1. device boots in unclaimed mode
2. user starts claim flow in mobile app
3. app transfers Wi-Fi credentials and claim token to device
4. device contacts Home OS provisioning endpoint or bootstrap MQTT flow
5. Home OS validates token and binds device to site
6. Home OS issues long-lived MQTT credentials and OTA channel
7. device stores credentials securely and reconnects as provisioned

### OTA

1. build firmware binary and manifest
2. sign manifest
3. upload artifact to Home OS
4. create OTA job
5. device checks for update
6. download over HTTPS
7. verify signature and hash
8. install to inactive partition
9. reboot and self-check
10. rollback on failure

## 19. Development Environment and Local Deployment

### Recommended Local Stack

- `hub-api`
- `automation-worker`
- `mosquitto`
- `assistant-runtime`
- `ollama`
- `sqlite` on local mounted storage

### Environment Defaults

```env
ALICE_SITE_ID=site_home_01
ALICE_TIMEZONE=Europe/London
DATABASE_URL=sqlite:///./data/alice.db
MQTT_HOST=mosquitto
MQTT_PORT=1883
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
PIPER_VOICE=en_GB-alan-medium
JWT_SECRET=dev-only-secret
```

### Local Bring-Up Order

1. start broker
2. start Home OS API
3. start automation worker
4. seed site, admin user, rooms
5. start assistant runtime
6. flash firmware targets
7. claim devices with mobile app

## 20. Deliverables

### Software

- FastAPI hub runtime skeleton
- assistant runtime skeleton
- mobile app shell
- web dashboard shell
- Docker Compose stack
- Mosquitto config

### Contracts

- MQTT topic taxonomy
- capability descriptor schema
- tool-call schema
- REST and WebSocket contracts

### Device

- shared ESP-IDF components
- sensor node firmware
- relay node firmware
- provisioning flow
- signed OTA flow

### Company Platform Structure

- future-proof monorepo tree
- placeholder READMEs for planned domains
- product-family structure for hardware
- manufacturing and compliance scaffolding

## 21. Implementation Plan

### Weeks 1-2

- scaffold repo and shared contracts
- create FastAPI skeleton and SQLite migrations
- define IDs, capability model, MQTT envelopes

### Weeks 3-4

- integrate broker and MQTT ingest
- implement device registry, entity projection, and state persistence
- build sensor and relay firmware skeletons

### Weeks 5-6

- implement commands, policy, audit
- deliver end-to-end telemetry and relay control
- start mobile and web shells

### Weeks 7-8

- finish core mobile and web screens
- build assistant runtime with push-to-talk
- connect tool gateway

### Weeks 9-10

- implement provisioning claim flow
- move firmware off hardcoded credentials
- implement automation engine MVP

### Weeks 11-12

- implement signed OTA path
- run reliability, security, and demo-home testing
- document installation and acceptance criteria

## 22. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope explosion | product slips | keep MVP to hub + sensor + relay + app + assistant |
| Assistant unpredictability | poor trust | constrain tool set and context |
| Firmware security work slows progress | delay | keep architecture compatible, stage hardening deliberately |
| Repo breadth becomes ceremony | wasted effort | keep placeholders documented but empty until activated |
| MQTT/state schema drift | brittle integrations | use versioned contracts from day one |

## 23. Later Upgrades

This structure supports later expansion without repo surgery:

- Thread and Matter device lines
- wall panel products
- TV and wearable experiences
- car integration
- cameras and local NVR
- router and access point products
- future phone-class hardware exploration
- manufacturing jigs and compliance evidence
- ML evaluation, fine-tuning, and voice asset pipelines

## 24. What Not to Build Yet

Do not build these in MVP v1:

- custom hub hardware
- far-field microphone arrays
- native camera/NVR stack
- Thread border router
- Matter controller as core path
- router or AP firmware
- wearable hardware
- TV OS
- phone hardware
- cloud fleet management
- plugin marketplace

Those all have a reserved place in the repo, but they are not active delivery work for MVP.
