# Alice Systems — Device Documentation
Version: 0.9  
Audience: embedded engineers, electronics engineers, industrial designers, firmware developers  
Status: detailed board-level planning document for living-room MVP and reusable room hardware

## 1. Purpose

This document defines the Alice living-room hardware stack in enough detail to:
- design first-pass PCBs
- define communication between boards and hub
- create development enclosures
- support firmware and integration planning
- reuse designs across other rooms

It intentionally focuses on **Alice-native hardware families**.

Important:
- temporary housing dimensions in this document are **development assumptions**
- mains-powered products require professional review and certified final enclosures
- blind dimensions are excluded because window-specific mechanical sizing cannot be accurately guessed for the house

---

## 2. Device strategy

The founder-defined MVP is one complete **living room**.  
That room should provide maximum product feel while also producing reusable hardware families for the rest of the home.

## 2.1 Living room device set
Target initial living-room hardware:
- HUB-H1 — Alice Hub
- SAT-V1 — Alice Voice Satellite (voice assistant module)
- ENV-S1 — Temperature / Humidity / Light Sensor
- PRES-P1 — Presence Detection Sensor
- SWR-1 — Smart Light Switch Controller
- OUT-R1 — Smart Plug / Socket Controller
- BLD-C1 — Blind Controller (custom mechanical sizing later)
- TV-A1 — TV Companion / Open Android Surface (nice-to-have in MVP, not critical path)

## 2.2 Reuse rule
Each device family should be reusable with minimal changes in:
- hallway
- bedroom
- kitchen
- bathroom
- kids room
- office

---

## 3. Communication model

## 3.1 Topology
All devices ultimately belong to one local hub.

```text
Alice Mobile App
    -> local setup / QR pairing
Alice Hub
    -> MQTT / local API / automation / assistant
Alice Devices
    -> publish telemetry and receive commands via local network
```

## 3.2 Communications stages

### Stage A — factory onboarding
Device is in onboarding mode.
Communications:
- BLE or SoftAP
- QR bootstrap identity
- no household trust yet

### Stage B — adoption
Phone acts as trusted introducer.
Communications:
- sends credentials
- confirms QR token
- requests adoption on hub

### Stage C — operational
Device communicates with hub using:
- Wi-Fi
- MQTT
- device-scoped credentials
- local-only default routing

## 3.3 Default transport choices
Recommended:
- QR for identity bootstrap
- BLE for low-friction onboarding when possible
- SoftAP fallback when BLE is awkward
- Wi-Fi for operational connectivity
- MQTT for runtime messaging

## 3.4 Topic pattern
Recommended namespace:
```text
alice/v1/hubs/{hub_id}/devices/{device_id}/telemetry
alice/v1/hubs/{hub_id}/devices/{device_id}/state
alice/v1/hubs/{hub_id}/devices/{device_id}/command
alice/v1/hubs/{hub_id}/devices/{device_id}/ack
alice/v1/hubs/{hub_id}/devices/{device_id}/health
```

## 3.5 Message classes
- telemetry
- state
- command
- acknowledgement
- health
- adoption status
- firmware update status

---

## 4. Common hardware platform rules

These rules apply to all Alice-native devices unless a board explicitly overrides them.

## 4.1 MCU family
Default embedded platform:
- **ESP32-S3** for feature-rich devices
- lighter ESP variants are allowed for cost-down later, but MVP should prefer consistency

Why:
- Wi-Fi + BLE
- strong ecosystem
- enough performance for rich peripherals
- easier shared firmware platform

## 4.2 Common board features
Where feasible, each board should include:
- unique device ID in firmware and label
- status LED
- reset button
- boot/pair button
- test pads
- programming/debug header or pogo points
- QR label area
- firmware version readable by app

## 4.3 Common firmware expectations
Each device firmware should support:
- onboarding mode
- credential intake
- secure adoption
- MQTT runtime
- health heartbeat
- OTA later
- factory reset path

## 4.4 Power classes
Devices fall into three power classes:
1. **low-power sensor**
2. **USB / external DC powered smart device**
3. **mains-powered control device**

Each class needs a different board and enclosure discipline.

---

## 5. Board catalog

## 5.1 HUB-H1 — Alice Hub

### Purpose
Local brain of the system.

### Responsibilities
- local API
- account store
- room/device registry
- automation engine
- logs and audit
- assistant runtime orchestration
- optional relay session
- local broker/client infrastructure

### Hardware approach
Recommended first implementation:
- compute module or SBC-class host, not ESP32
- separate carrier board if desired later
- Ethernet + Wi-Fi
- local SSD or eMMC storage
- passive cooling preferred if possible

### Inputs / outputs
- power input
- Ethernet
- Wi-Fi
- Bluetooth optional
- USB service/debug
- status LED
- recovery button

### Board target
If custom carrier board is built:
- PCB target: 100 mm x 100 mm to 120 mm x 120 mm

### Temporary housing
Development enclosure target:
- 160 mm x 160 mm x 45 mm
- vented top and bottom
- removable base plate
- rear cut-outs for Ethernet, power, service USB

### Notes
Hub industrial design matters because it is a flagship object.  
Even the dev enclosure should feel cleaner than a generic project box.

---

## 5.2 SAT-V1 — Alice Voice Satellite

### Purpose
A tabletop voice interaction module for the living room, conceptually closer to a small speaker puck than a wall sensor.

### Product role
- wake listening later
- push-to-talk initially
- mic input
- speaker output
- local voice UX
- ambient status glow

### Core functions
- capture voice
- stream audio to hub or companion runtime
- play TTS/audio responses
- show status via ring or face LED
- act as household presence touchpoint

### Electrical architecture
Recommended:
- ESP32-S3 main controller
- microphone array or at least 2 digital MEMS mics for MVP-plus
- class-D speaker amp
- small full-range speaker
- capacitive or physical action button
- LED ring or front light diffuser
- USB-C power

### Suggested interfaces
- I2S for microphones
- I2S for audio codec or amp path
- GPIO for button and LED control
- UART/pogo for bring-up
- optional local temperature sensor for thermal monitoring

### Recommended PCB strategy
Two-board approach preferred:
1. main logic board
2. mic/LED daughterboard or top board

### Board target
Main board:
- 78 mm x 78 mm square
or
- 80 mm diameter round equivalent

### Temporary housing
Development enclosure target:
- 95 mm diameter
- 42 mm height

Reasoning:
- large enough for speaker cavity
- small enough for side table or shelf
- visually comparable to a voice puck without copying anyone directly

### External features
- QR code underside
- LED ring or front status arc
- one multifunction button
- mute switch recommended
- USB-C rear or underside

### Software notes
For MVP:
- push-to-talk acceptable
- wake word optional if stable
- should support full conversational assistant, not only home commands

---

## 5.3 ENV-S1 — Temperature / Humidity / Light Sensor

### Purpose
A compact room environment sensor for the living room and later wider house reuse.

### Core functions
- temperature
- humidity
- ambient light

### Recommended sensor stack
- digital temp/humidity sensor
- digital ambient light sensor
- optional battery measurement if battery-powered variant later

### Electrical architecture
- ESP32-S3 or smaller ESP variant
- I2C sensor bus
- low-noise local regulation
- LED and pairing button
- optional battery or USB power variant

### Board target
- PCB: 38 mm x 38 mm

### Temporary housing
- 50 mm x 50 mm x 22 mm

### External design notes
- front venting for temp/humidity
- light sensor window
- clean wall or shelf placement
- detachable rear plate helpful

### Placement notes
- avoid direct sun
- avoid placing close to TV exhaust or speaker amps
- avoid dead air pockets

---

## 5.4 PRES-P1 — Presence Detection Sensor

### Purpose
Room-level human presence detection for more accurate automations than simple PIR alone.

### Product role
- detect continuous presence
- supplement motion sensing
- support occupancy-aware automations

### Detection strategy
Recommended MVP options:
- mmWave-based presence sensor
- or high-quality PIR + occupancy logic if mmWave is deferred

### Electrical architecture
- ESP32-S3
- mmWave sensor module UART or other supported interface
- status LED
- calibration button optional
- USB or low-voltage DC input

### Board target
- PCB: 55 mm x 35 mm

### Temporary housing
- 70 mm x 45 mm x 28 mm

### Housing notes
- sensor face needs clean forward exposure
- wall or shelf mount
- tilt-adjustable temporary mount recommended for calibration

### Placement notes
- aimed into seating area
- avoid metal obstructions
- should not sit immediately behind the TV

---

## 5.5 SWR-1 — Smart Light Switch Controller

### Purpose
Alice-native in-wall or behind-switch controller for lights.

### Product role
- on/off switching
- possible dimmer variant later
- physical switch state awareness
- integration into local automations

### Important warning
This is a **mains-powered board class**.  
Temporary enclosures are for bench and controlled development only.

### Electrical architecture
Recommended first split:
- low-voltage logic side
- isolated or safely separated mains switching side
- relay-based switching first
- dimming variant later as separate board family if needed

### Functional requirements
- manual switch input
- relay output
- local override still works if hub unavailable
- device reports state to hub
- safe startup behaviour after power loss configurable

### Board target
- PCB: 46 mm x 38 mm for controller core
- may require variant dimensions depending on wall-box target later

### Temporary housing
Bench development housing only:
- 60 mm x 50 mm x 25 mm
- flame-retardant prototype enclosure material strongly preferred
- no user-facing deployment in temporary housing

### Integration note
Final wall-install dimensions must be adapted to the actual region-specific switch/back-box format.  
Do not freeze final industrial dimensions yet.

---

## 5.6 OUT-R1 — Smart Plug / Socket Controller

### Purpose
Control switched outlets or create an Alice-native smart plug/socket product family.

### Product role
- switch outlet on/off
- optional energy monitoring later
- schedule and automation participation

### Safety class
Mains-powered.  
Requires the same caution level as SWR-1.

### Electrical architecture
Recommended:
- relay or appropriate switching stage
- optional current/power measurement IC later
- isolated supply
- separated logic and mains domains
- ESP32 logic section

### Board target
- PCB: 50 mm x 42 mm for control core

### Temporary housing
Bench development enclosure only:
- 70 mm x 55 mm x 28 mm

### Product strategy note
There are two likely product paths:
1. plug-in smart plug product
2. integrated smart socket controller

For MVP, focus on the controller electronics and Alice UX, not final certified mains packaging.

---

## 5.7 BLD-C1 — Blind Controller

### Purpose
Control motorised blinds in the living room.

### Scope boundary
Mechanical blind size and final housing dimensions are intentionally excluded because they depend on actual window dimensions and installation method.

### What is in scope here
- the control electronics
- communication model
- integration into Alice
- power and I/O expectations

### Electrical architecture
Recommended:
- ESP32-S3 control board
- motor driver or relay outputs depending on motor type
- limit input support
- manual up/down input
- calibration mode
- optional position feedback path

### Board target
- PCB: 60 mm x 45 mm

### Temporary controller housing
If using a separate controller box for development:
- 80 mm x 60 mm x 25 mm

### Notes
The blind motor, track, brackets, and custom fitting are separate mechanical workstreams.

---

## 5.8 TV-A1 — TV Companion / Open Android Surface

### Purpose
A TV-facing Alice surface that can show the home and optionally interact with Alice from the living room.

### MVP importance
Not critical-path for the first successful living-room loop, but valuable as an early differentiator.

### Product role
- room dashboard
- assistant surface
- alerts
- media and home context
- maybe TV control bridge

### Hardware/product direction
Two possible paths:
1. Android app on commodity device
2. custom open Android companion box

The founder preference is toward a **custom Android-based route**, not only a standard app.

### Board target for a companion box
If creating an Alice TV companion box:
- PCB: 90 mm x 70 mm

### Temporary housing
- 115 mm x 85 mm x 28 mm

### Interfaces
- HDMI
- USB-C power
- Wi-Fi / Bluetooth
- service port

### Notes
For earliest MVP, treat TV as a surface and integration target, not as a blocker for core home intelligence.

---

## 6. Common electrical design guidance

## 6.1 Common low-voltage interface set
Where feasible across non-mains boards:
- USB-C 5 V input or low-voltage JST input
- debug UART pads
- BOOT and RESET access
- I2C expansion header optional
- speaker/mic connectors where relevant

## 6.2 Status interface consistency
Every Alice device should expose a simple consistent human-readable state:
- booting
- pairing
- adopted
- online
- error

This can be expressed through:
- single LED
- RGB status LED
- ring light on voice products

## 6.3 QR code placement
Each device should reserve:
- visible QR on box
- visible QR on product exterior or underside
- human-readable fallback short code nearby

## 6.4 Board revision marking
All PCBs must include:
- board name
- revision
- date code
- test point labels where space allows

---

## 7. Firmware requirements per board class

## 7.1 All boards
Must implement:
- unique device ID
- onboarding mode
- adoption confirmation
- MQTT connection
- heartbeat
- version reporting
- factory reset

## 7.2 Sensor boards
Must implement:
- sample intervals
- state change thresholds
- calibration values
- sane power-fail recovery

## 7.3 Control boards
Must implement:
- safe default output state
- local/manual override
- command acknowledgement
- last-known-state restore policy

## 7.4 Voice board
Must implement:
- audio path initialisation
- low-latency local transport to hub
- mute state
- status feedback
- assistant session state

---

## 8. Temporary housing strategy

Temporary housings should be:
- printable
- easy to revise
- assembly-friendly
- not over-optimised too early

## 8.1 Materials
Recommended prototype progression:
- PLA for quick shape checks
- PETG for more durable prototypes
- ABS or stronger material for hot/near-final prototype rounds

## 8.2 Housing rules
- include QR recess or flat label area
- include test access if still in development
- allow non-destructive re-open
- provide cable relief where needed
- keep enough air path for thermal comfort

## 8.3 Visual identity even in dev
Even development housings should:
- feel coherent as a family
- share corner radii and vent language where sensible
- use consistent indicator placement

---

## 9. Device naming and family codes

Recommended family naming:

- HUB-H1 — Hub
- SAT-V1 — Voice Satellite
- ENV-S1 — Environment Sensor
- PRES-P1 — Presence Sensor
- SWR-1 — Switch Relay
- OUT-R1 — Outlet Relay
- BLD-C1 — Blind Controller
- TV-A1 — TV Android Companion

Rationale:
- readable by humans
- sortable by family
- revision-friendly

---

## 10. Living room reference deployment

A first complete living room could look like this:

- 1x HUB-H1 in cabinet or sideboard
- 1x SAT-V1 on side table or shelf
- 1x ENV-S1 on wall or shelf
- 1x PRES-P1 aimed at seating area
- 1x SWR-1 controlling main light circuit
- 1x OUT-R1 controlling one or more outlet paths
- 1x BLD-C1 connected to blinds motor
- 1x TV-A1 or TV software surface

This single room then proves:
- sensing
- control
- voice
- presence
- scene logic
- assistant conversation
- premium UI

---

## 11. Minimal BOM-class guidance by board

## 11.1 SAT-V1
Needs:
- ESP32-S3
- 2x to 4x digital MEMS mics
- amplifier
- speaker
- LED ring or RGB LEDs
- button(s)
- power input stage

## 11.2 ENV-S1
Needs:
- ESP32-S3 or reduced ESP
- temp/humidity sensor
- light sensor
- LED
- pairing/reset button
- power input stage

## 11.3 PRES-P1
Needs:
- ESP32-S3
- presence sensor module
- LED
- power stage
- optional mount hardware

## 11.4 SWR-1
Needs:
- ESP32 logic section
- isolated or separated power stage
- relay or switching element
- input sensing
- safe enclosure plan
- test isolation discipline

## 11.5 OUT-R1
Needs:
- ESP32 logic section
- switching element
- optional energy metering
- separated mains and logic design

## 11.6 BLD-C1
Needs:
- ESP32-S3
- motor driver or relay controls
- input terminals
- optional calibration buttons
- fault handling

---

## 12. Safety and certification notes

This document is for product architecture and development planning.  
It is **not** a substitute for certified mains design, EMC work, thermal validation, or region-specific compliance review.

Mandatory caution areas:
- switch controller
- socket controller
- blinds controller if mains motor path is used
- power supplies across all products

Temporary housings for these devices are:
- development only
- not consumer deployable
- not a substitute for certified enclosures

---

## 13. Immediate next hardware actions

## 13.1 Highest-value board order
1. ENV-S1
2. SAT-V1
3. PRES-P1
4. SWR-1 bench controller
5. OUT-R1 bench controller
6. BLD-C1
7. TV-A1 as companion later

## 13.2 Why this order
- ENV-S1 and PRES-P1 give room intelligence quickly
- SAT-V1 proves the Alice experience
- SWR-1 and OUT-R1 prove actuation
- BLD-C1 adds premium value once actuation path is stable

---

## 14. Final statement

The living-room hardware set is not a one-room dead end.

It should be treated as the first **Alice device platform library**:
- one assistant surface
- one sensing stack
- one presence stack
- one switching stack
- one outlet stack
- one blind-control stack

If built properly, that becomes most of the house.
