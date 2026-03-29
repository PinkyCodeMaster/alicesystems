# Alice Systems — Technical Specification
Version: 0.9  
Audience: senior software engineers, technical leads, solutions architects  
Status: implementation draft for MVP + near-term expansion

## 1. Purpose

This document translates the Alice product vision into a buildable technical system.

It is written so that a senior software developer or small technical team can:
- understand the architecture
- design service boundaries
- define data models and APIs
- implement the founder-defined MVP
- extend the platform beyond the living room

This document assumes the founder-defined MVP is a **polished single-household living-room pilot**, not a stripped demo.

---

## 2. Scope definition

## 2.1 In scope for this spec
- local-first Home OS
- mobile and web applications
- household identity and ownership model
- hub claim flow
- QR-based device adoption flow
- assistant architecture for home and general reasoning
- remote access without opening router ports
- living-room device support
- reusable device architecture for future rooms

## 2.2 Out of scope for this version
- manufacturing certification details
- app-store/legal policy detail
- cloud-scale multi-tenant billing systems
- third-party marketplace architecture
- production-grade fleet management beyond basic update channels

---

## 3. Foundational technical position

Alice should be implemented as a **hub-centric local platform** with optional remote services.

### System of record
The **hub** is authoritative for:
- household structure
- users
- devices
- current state
- automations
- logs
- memory
- assistant home context

### Cloud role
The cloud is optional and may provide:
- relay/brokered remote access
- notifications
- encrypted offsite backup
- optional cloud AI augmentation
- software distribution metadata

The cloud must never become the mandatory source of truth for core home operations.

---

## 4. Architecture overview

```text
+---------------------------------------------------------------+
|                        Alice Mobile App                       |
|             setup, daily control, chat, voice, alerts         |
+--------------------------+------------------------------------+
                           |
                           | local HTTPS / WebSocket
                           | or brokered remote session
                           v
+---------------------------------------------------------------+
|                          Alice Hub                            |
|                                                               |
|  +----------------+   +----------------+   +---------------+  |
|  | API Gateway    |   | State Engine   |   | Audit Engine  |  |
|  | Auth           |   | Rooms/Devices  |   | Event Journal |  |
|  +----------------+   +----------------+   +---------------+  |
|                                                               |
|  +----------------+   +----------------+   +---------------+  |
|  | Automation     |   | Device Manager |   | Memory Store  |  |
|  | Rules/Scenes   |   | Adoption       |   | Preferences   |  |
|  +----------------+   +----------------+   +---------------+  |
|                                                               |
|  +----------------+   +----------------+   +---------------+  |
|  | Assistant      |   | Tool Router    |   | Relay Agent   |  |
|  | Chat/Voice     |   | Policy Checks  |   | Optional      |  |
|  +----------------+   +----------------+   +---------------+  |
|                                                               |
|  +----------------+   +----------------+                      |
|  | MQTT Broker    |   | Local DB       |                      |
|  | or MQTT Client |   | SQLite -> PG   |                      |
|  +----------------+   +----------------+                      |
+---------------------------------------------------------------+
                           ^
                           |
                           | MQTT / provisioning / local APIs
                           |
+--------------------------+------------------------------------+
|                     Alice Devices                             |
|  sensors, switches, plugs, blinds, voice satellite, etc.      |
+---------------------------------------------------------------+
```

---

## 5. Recommended stack

## 5.1 Hub/backend
Recommended default:
- **Python**
- **FastAPI** for HTTP/WebSocket API
- **Pydantic** for schemas
- **SQLite** for MVP
- **PostgreSQL** for scale-up path
- **MQTT** for device messaging
- **Redis optional later** for task/event fan-out and caching
- **Docker Compose** for local deployment
- **systemd + containers** for appliance-style deployment

Why this stack:
- Python matches the AI orchestration layer well
- FastAPI gives clean async APIs and schema discipline
- SQLite is fast for MVP iteration
- migration path to PostgreSQL is straightforward

## 5.2 Native app
Recommended:
- **React Native + Expo**

Why:
- fast iteration
- strong mobile ecosystem
- shared code with future companion clients possible

## 5.3 Web UI
Recommended:
- **Next.js**
- TypeScript
- shared design system with mobile where sensible

## 5.4 Firmware
Recommended:
- **ESP-IDF**
- C/C++
- MQTT client library
- BLE/SoftAP provisioning
- OTA pipeline

## 5.5 AI
Recommended local-first strategy:
- STT: Whisper-class or lightweight local STT
- LLM runtime: local inference service on hub
- TTS: local TTS engine
- deterministic tool layer
- optional cloud augmentation later

---

## 6. Runtime decomposition

Alice should be implemented as three main runtimes.

## 6.1 Home OS runtime
Runs on the hub.

Responsibilities:
- API
- auth
- state graph
- device registry
- automation engine
- memory persistence
- audit/event logging
- relay/session management
- tool access for assistant

## 6.2 Assistant runtime
Runs locally on the hub or a companion compute node if needed.

Responsibilities:
- conversation sessions
- STT/TTS orchestration
- LLM prompt/context building
- separation of general vs home reasoning
- tool requests
- assistant memory reads/writes
- response synthesis

## 6.3 Device runtime
Runs on embedded hardware.

Responsibilities:
- bootstrap pairing
- receive credentials
- publish telemetry
- receive commands
- report health
- support updates

---

## 7. Domain model

## 7.1 Core entities

### Household
Represents one home context.

Fields:
- household_id
- name
- timezone
- locale
- created_at
- owner_user_id

### Hub
Represents a physical installed Alice hub.

Fields:
- hub_id
- household_id
- claim_state
- serial_number
- firmware_version
- local_network_info
- relay_enabled
- created_at
- claimed_at

### User
Represents a person with authentication access.

Fields:
- user_id
- household_id
- full_name
- email
- password_hash
- role
- app_enabled
- created_at

### Occupant
Represents a household person whether or not they use the app.

Fields:
- occupant_id
- household_id
- display_name
- relationship
- linked_user_id nullable
- notes
- created_at

### Room
Represents a physical logical area.

Fields:
- room_id
- household_id
- name
- floor
- room_type
- sort_order

### Device
Represents an adopted device.

Fields:
- device_id
- household_id
- room_id
- device_type
- hardware_model
- firmware_version
- adoption_state
- connectivity_state
- display_name
- last_seen_at

### Automation
Represents a rule/scenario.

Fields:
- automation_id
- household_id
- name
- enabled
- trigger_json
- condition_json
- action_json
- created_by
- updated_at

### AuditEvent
Represents a durable record of what happened.

Fields:
- event_id
- household_id
- event_type
- actor_type
- actor_id
- source_type
- source_id
- summary
- detail_json
- timestamp

### MemoryItem
Represents an assistant-memory fact or preference.

Fields:
- memory_id
- household_id
- scope_type
- scope_id
- category
- body
- provenance
- confidence
- editable
- deletable
- created_at
- updated_at

### DeviceCredential
Represents per-device auth material.

Fields:
- credential_id
- device_id
- auth_type
- public_material
- rotation_version
- issued_at
- revoked_at nullable

---

## 8. Ownership and identity model

## 8.1 Ownership hierarchy
```text
Household
  -> Hub
  -> Users
  -> Occupants
  -> Rooms
  -> Devices
  -> Automations
  -> Memory
```

## 8.2 Local account model
The initial owner account is created **on the hub**.

Important:
- app install does not equal cloud signup
- app can be used as a local claim client before any cloud is involved
- credentials are validated by the hub

## 8.3 Roles
Recommended initial roles:
- owner
- admin
- member
- child
- guest

---

## 9. Hub claim flow — technical

## 9.1 Goals
- physical-proximity required
- simple UX
- one-time claim
- no default shared credential dependence

## 9.2 Required components
Hub ships with:
- hardware serial
- bootstrap keypair or signed bootstrap secret
- QR claim payload
- temporary BLE or local AP onboarding mode

## 9.3 Claim sequence
1. App scans QR.
2. App parses:
   - hub_id
   - claim token
   - onboarding endpoint hint
3. App connects locally to hub.
4. Hub presents claim challenge.
5. App submits:
   - QR token
   - owner account payload
   - optional home metadata
6. Hub validates token and unclaimed state.
7. Hub creates household + owner.
8. Hub rotates bootstrap material.
9. Hub enters claimed operational mode.

## 9.4 Claim state machine
States:
- factory_unclaimed
- claim_in_progress
- claimed
- transfer_pending
- factory_reset_required

---

## 10. House plan setup — technical

Rooms should be created early because they anchor:
- naming
- device placement
- automation composition
- assistant reasoning

## 10.1 Room model requirements
- rooms can exist without devices
- devices can move between rooms
- rooms can have aliases
- room types can drive UI defaults

## 10.2 Suggested room types
- living_room
- kitchen
- hallway
- bathroom
- bedroom
- office
- nursery
- utility
- outdoor
- custom

---

## 11. Device adoption flow — technical

## 11.1 Design principles
- QR starts trust
- local transport delivers credentials
- hub approves final adoption
- user names and places device
- device cannot silently self-adopt

## 11.2 Adoption states
- discovered
- awaiting_pair
- credentials_sent
- awaiting_hub_approval
- adopted
- quarantined
- removed

## 11.3 Device QR payload
Suggested fields:
- device_id
- model
- hw_revision
- bootstrap_pubkey or signed token
- manufacturing batch
- onboarding transport hint
- checksum

## 11.4 Provisioning transport
Recommended first implementation:
- BLE provisioning where practical
- SoftAP fallback when BLE is impractical
- phone-assisted credential handoff

## 11.5 Credentials delivered
At minimum:
- household/network join credentials
- device certificate or token
- MQTT broker address
- device topic namespace
- initial config payload

## 11.6 Post-adoption metadata
The app must collect:
- display name
- room
- category override
- icon suggestion
- calibration or operating mode if relevant

---

## 12. Device communication architecture

## 12.1 Messaging backbone
Recommended: MQTT

Why:
- fits embedded devices
- good publish/subscribe model
- natural for telemetry and commands
- easy to scope by topic

## 12.2 Topic design
Suggested namespace:

```text
alice/v1/hubs/{hub_id}/devices/{device_id}/telemetry
alice/v1/hubs/{hub_id}/devices/{device_id}/state
alice/v1/hubs/{hub_id}/devices/{device_id}/command
alice/v1/hubs/{hub_id}/devices/{device_id}/ack
alice/v1/hubs/{hub_id}/devices/{device_id}/health
```

## 12.3 Message envelope
Suggested standard envelope:

```json
{
  "schema": "alice.telemetry.env@1",
  "message_id": "uuid-or-ulid",
  "timestamp": "2026-03-29T12:00:00Z",
  "hub_id": "hub_123",
  "device_id": "env_s1_001",
  "payload": {},
  "signature": {}
}
```

## 12.4 Command envelope
```json
{
  "schema": "alice.command.switch@1",
  "message_id": "uuid-or-ulid",
  "timestamp": "2026-03-29T12:00:00Z",
  "device_id": "swr_001",
  "command": {
    "type": "set_output",
    "channel": "main",
    "value": true
  }
}
```

---

## 13. API architecture

## 13.1 API boundaries
The API should be split conceptually into:
- auth
- household
- rooms
- devices
- automations
- assistant
- audit
- remote session

## 13.2 Core endpoints

### Auth
- `POST /v1/auth/local-login`
- `POST /v1/auth/create-owner`
- `POST /v1/auth/create-member`
- `POST /v1/auth/refresh`

### Hub claim
- `POST /v1/hub/claim/start`
- `POST /v1/hub/claim/complete`

### Household
- `GET /v1/household`
- `PATCH /v1/household`

### Rooms
- `GET /v1/rooms`
- `POST /v1/rooms`
- `PATCH /v1/rooms/{room_id}`

### Occupants
- `GET /v1/occupants`
- `POST /v1/occupants`
- `PATCH /v1/occupants/{occupant_id}`

### Devices
- `GET /v1/devices`
- `GET /v1/devices/pending`
- `POST /v1/devices/adopt`
- `PATCH /v1/devices/{device_id}`
- `POST /v1/devices/{device_id}/action`

### Automations
- `GET /v1/automations`
- `POST /v1/automations`
- `PATCH /v1/automations/{automation_id}`
- `POST /v1/automations/{automation_id}/enable`
- `POST /v1/automations/{automation_id}/disable`

### Assistant
- `POST /v1/assistant/chat`
- `POST /v1/assistant/tool-call`
- `GET /v1/assistant/history`
- `GET /v1/assistant/memory`
- `PATCH /v1/assistant/memory/{memory_id}`
- `DELETE /v1/assistant/memory/{memory_id}`

### Audit
- `GET /v1/audit`
- `GET /v1/audit/{event_id}`

---

## 14. WebSocket architecture

The mobile app and web UI should subscribe to live state through a WebSocket channel.

## 14.1 Uses
- live room state updates
- device health changes
- pending device adoption
- automation run events
- assistant status
- alert and notification delivery

## 14.2 Event types
- room.state.updated
- device.state.updated
- device.pending.discovered
- automation.run.started
- automation.run.completed
- assistant.message.created
- assistant.tool.executed
- system.alert.created

---

## 15. Assistant architecture

The assistant is a product in itself.

## 15.1 Required capabilities
The assistant must reason across three domains:

### Home domain
- devices
- rooms
- automations
- history
- explanations

### Personal household domain
- occupants
- preferences
- routines
- local notes or reminders later

### General reasoning domain
- math
- homework
- explanations
- Q&A
- productivity prompts
- general conversation

## 15.2 Important separation
The assistant should not mix these blindly.

Recommended context layers:
1. system prompt
2. household state context
3. user/occupant context
4. task-specific tool context
5. general reasoning context

## 15.3 Tooling model
Assistant should never directly execute home actions from raw text.

Recommended flow:
1. user request
2. interpret intent
3. decide whether this is:
   - pure chat
   - general tool request
   - home tool request
4. submit structured tool request
5. policy engine validates
6. tool executes
7. response generated
8. audit event written

## 15.4 Initial non-home tools
Recommended day-one non-home tools:
- calculator
- timer
- reminder
- note save
- simple knowledge retrieval from local model
- optional safe web search later
- homework explainer
- unit conversion

## 15.5 Memory model
Memory must be:
- scoped
- inspectable
- editable
- deletable

Memory categories:
- user preferences
- home facts
- device nicknames
- occupant facts
- assistant conventions
- derived patterns

---

## 16. AI runtime strategy

## 16.1 Local by default
The preferred path is:
- local STT
- local LLM
- local TTS

## 16.2 Optional cloud augmentation
Allowed later for:
- larger reasoning tasks
- difficult general Q&A
- fallback transcription
- search-backed answers

This must be user-controlled and clearly disclosed.

## 16.3 Founder-defined assistant requirement
The MVP assistant is not limited to home commands.
It must feel like a real assistant in a conversational interactive manner.

That means the assistant service must support:
- multi-turn context
- interruption handling later
- general questions
- basic tutoring/help behaviour
- natural language home control
- explanation of system actions

---

## 17. Remote access architecture

## 17.1 Product requirement
Remote app access must work without requiring the user to open router ports.

## 17.2 Recommended design
The hub runs a **relay agent** that maintains an outbound secure connection to Alice Cloud or a self-hosted relay.

### Flow
```text
Phone app -> relay endpoint -> hub outbound session -> hub API
```

## 17.3 Connection modes
### Mode A — Local direct
App is on same LAN.
- preferred
- lowest latency

### Mode B — Brokered remote
App is away from home.
- uses outbound relay session
- no inbound port opening

### Mode C — Private mesh
Power-user option later.

## 17.4 Rule
The app should automatically prefer:
1. local direct
2. brokered remote
3. offline cached state

---

## 18. Security architecture

## 18.1 Identity
- unique hub identity
- unique per-device identity
- per-user local accounts
- short-lived app sessions
- secure credential rotation path

## 18.2 Secrets
Secrets must not be embedded as shared factory defaults.
Bootstrap secrets must rotate on claim/adoption.

## 18.3 Assistant safety
- tool-gated
- audit logged
- permission checked
- risky actions require confirmation

## 18.4 Logging
All meaningful actions create audit events, but:
- secrets must not be logged
- raw private content retention should be controlled
- assistant transcripts should have explicit retention policy

## 18.5 Mains device caution
For switch, socket, and blinds controllers:
- mains-side design must be isolated and professionally reviewed
- development enclosures must not be mistaken for certified final products

---

## 19. UI architecture requirements

## 19.1 Native app quality bar
The native app must feel polished, not like a debug wrapper around APIs.

Requirements:
- consistent design system
- onboarding that feels premium
- responsive room/device cards
- stable offline/local connection model
- chat and voice assistant surface

## 19.2 Web UI quality bar
The web UI must:
- feel like a real product admin surface
- support deeper automation composition
- support richer review and diagnostics
- share mental models with mobile, not clone screens blindly

## 19.3 Shared design system
Recommended shared primitives:
- typography scale
- room cards
- state badges
- action rows
- timeline event cards
- assistant message components
- onboarding step layouts

---

## 20. Automation model

## 20.1 Automation structure
Each automation should consist of:
- trigger
- conditions
- actions
- optional explanation metadata

## 20.2 Builder levels
### Simple builder
Mobile-friendly
- templates
- common triggers
- room-oriented setup

### Advanced builder
Web-first
- multiple conditions
- schedules
- scenes
- chaining
- reusable variables later

## 20.3 Example
Trigger:
- living room presence detected

Conditions:
- after sunset
- TV off

Actions:
- turn on lamp to 30 percent
- close blinds if glare threshold exceeded

---

## 21. Observability and diagnostics

## 21.1 Metrics
Hub should record:
- device online/offline
- last seen
- automation execution success/fail
- assistant latency
- relay connection state
- queue depth or message backlog
- local model load times

## 21.2 Debug surfaces
Web UI should show:
- live event stream
- recent audit trail
- pending adoption events
- device health
- automation run history

---

## 22. Testing strategy

## 22.1 Levels
- unit tests
- service contract tests
- device simulator tests
- onboarding flow tests
- UI integration tests
- hardware-in-loop tests for key devices

## 22.2 Minimum acceptance tests for MVP
1. new hub can be claimed locally via QR
2. household owner account is created locally
3. rooms can be defined before devices
4. occupant records can include non-app users
5. new device can be adopted via QR
6. device receives credentials and joins hub
7. living room devices appear correctly in UI
8. simple automation can be created on mobile
9. complex automation can be edited on web
10. assistant can answer a general question
11. assistant can control a home device
12. assistant can explain why a device changed state
13. remote access works without port forwarding

---

## 23. Delivery plan

## Phase A — platform spine
- FastAPI hub
- auth
- rooms
- devices
- WebSocket updates
- mobile onboarding
- QR claim

## Phase B — living room hardware and adoption
- environment sensor
- presence sensor
- light switch
- plug control
- voice satellite
- first polished room views

## Phase C — assistant maturity
- chat
- voice
- general Q&A
- home tool control
- memory basics
- explanation engine

## Phase D — polish and remote
- web automation builder
- relay-based remote access
- better history
- more resilient error handling
- installability and update flow

---

## 24. Recommended repository structure

```text
alice/
  apps/
    mobile/
    web/
  services/
    hub_api/
    assistant/
    automation/
    relay/
    device_simulator/
  firmware/
    common/
    env_s1/
    pres_p1/
    swr_1/
    out_r1/
    sat_v1/
    bld_c1/
  hardware/
    electronics/
      boards/
      common/
      libraries/
      test/
  docs/
    master/
    technical/
    devices/
  infra/
    docker/
    deployment/
    ci/
```

---

## 25. Final implementation note

A senior developer should treat Alice as three tightly coupled products:
1. a local operating system for the home
2. a device platform
3. a conversational assistant

If any one of those is treated as an afterthought, the product will feel incomplete.
