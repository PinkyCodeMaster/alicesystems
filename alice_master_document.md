# Alice Systems — Master Document
Version: 0.9  
Audience: founder, product, design, engineering, operations  
Status: working master document

## 1. Purpose

This document is the single readable source of truth for what **Alice Systems** is, what it is not, how it should feel, how a household adopts it, and what the founder-defined MVP must deliver.

It is written to be understandable by:
- founder and stakeholders
- designers
- senior engineers
- future operators and support staff

It is intentionally product-led first, not code-led first.

---

## 2. Product definition

**Alice Systems** is a **local-first, privacy-first virtual butler and home operating system**.

Alice is not only a smart-home controller.  
Alice is a household intelligence layer that can:
- understand the home
- understand the people in it
- control trusted devices
- explain what it did and why
- help with non-home tasks such as questions, explanations, mathematics, homework support, reminders, and day-to-day assistance

### 2.1 What Alice is
Alice is:
- a **local hub** that owns the household state
- a **mobile-first experience** for setup and daily use
- a **web interface** for deeper configuration and complex automations
- an **optional AI assistant** that can converse about both the home and general topics
- a **device ecosystem** built around secure QR-based adoption

### 2.2 What Alice is not
Alice is not:
- a cloud account that happens to control some devices
- a generic chatbot bolted onto home automation
- a settings-heavy hobbyist dashboard
- a business model based on harvesting household data

---

## 3. Non-negotiable principles

## 3.1 Local-first
Core functionality must work locally:
- hub claim
- user authentication
- room model
- device adoption
- device control
- automations
- logs
- assistant access to home state
- assistant help for general reasoning tasks when the local model is present

The cloud, if enabled, is an enhancement layer — not the system of record.

## 3.2 Privacy-first
By default:
- no mandatory cloud account
- no external telemetry required
- no open inbound router ports required
- no company ownership of household data

## 3.3 User ownership
The household owns:
- the hub
- the data
- the device relationships
- the memory and preferences
- the ability to export, reset, or delete

## 3.4 Mobile-first
At least 90 percent of the customer journey should be possible and pleasant from the mobile app:
- claim hub
- create household
- define rooms
- add family members
- adopt devices
- create simple automations
- enable or skip AI
- use Alice daily

## 3.5 Explainability
If Alice acts, the user must be able to answer:
- what happened
- when it happened
- why it happened
- who or what triggered it

## 3.6 Safety over cleverness
Alice can feel magical, but it cannot feel dangerous or random.

---

## 4. Product surfaces

Alice has four major surfaces.

### 4.1 Alice Hub
The local brain in the home.

Responsibilities:
- household data ownership
- user accounts
- device registry
- automation engine
- logs and audit
- local AI orchestration
- optional remote relay session

### 4.2 Mobile app
The primary user surface.

Responsibilities:
- onboarding
- daily control
- alerts
- room views
- assistant chat/voice
- quick automations
- household management

### 4.3 Web UI
The advanced surface.

Responsibilities:
- complex automation creation
- debugging and review
- deeper device configuration
- richer history and audit browsing
- administration

### 4.4 Device ecosystem
Includes both Alice-native hardware and integrations.

Initial Alice-native hardware focus:
- hub
- voice assistant satellite
- environment sensor
- presence sensor
- light switch controller
- smart plug/socket controller
- blinds controller
- TV companion / custom Android surface later

---

## 5. Household model

Alice should think in this order:

1. household
2. people
3. rooms
4. devices
5. states
6. routines
7. assistant behaviour

### 5.1 Core entities
- Household
- Hub
- Owner
- Members
- Occupants
- Rooms
- Devices
- Automations
- Scenes
- Memory items
- Audit events

### 5.2 Occupants vs app users
Alice must support people who live in the home but do not use the app.

Examples:
- spouse without app access yet
- children
- relatives
- guests
- carers

This matters because the assistant and automation system should model the household, not only the installed apps.

---

## 6. Foundational setup flow

This is the canonical first-run experience.

## 6.1 Before first boot
User purchases:
- Alice Hub
- optionally one or more Alice devices

Each hub and device ships with:
- printed QR code on box
- matching QR code on product
- unique identity
- secure bootstrap token

## 6.2 Hub claim flow
1. User downloads the Alice mobile app.
2. User powers on the hub.
3. User scans the QR code on the hub or the box.
4. The phone connects locally to the hub.
5. The app opens the claim flow.
6. The user creates a **local household owner account** on the hub.

Important:
- this is **not** a mandatory cloud signup
- the email field exists for identity, recovery, and optional remote services later
- all core account data is created and stored locally first

## 6.3 Owner account fields
- full name
- email address
- password

## 6.4 House plan setup
After account creation, the user defines the home structure.

The setup should encourage entering all real rooms, even if no devices exist there yet.

Example room list:
- living room
- kitchen
- hallway downstairs
- downstairs bathroom
- hallway upstairs
- upstairs bathroom
- master bedroom
- kids room

Design rule:
**Rooms come before devices.**  
Alice must model the house as a place, not as a bag of gadgets.

## 6.5 Family and occupants
After rooms, user adds family members and occupants.

Fields per person:
- name
- relationship or role
- uses app: yes/no
- voice profile later: optional
- permissions later: optional

This step should be skippable, but strongly recommended.

## 6.6 First device adoption
The user is then asked whether they want to adopt a first device.
- yes: launch adoption flow
- skip: finish setup and continue later

## 6.7 AI assistant choice
User is asked:
- enable AI assistant now
- or continue with non-AI smart-home mode first

This must be optional.

---

## 7. Device adoption philosophy

Discovery is not ownership.  
Detection is not trust.  
**Adoption** is the moment a household approves and binds a device.

## 7.1 Device adoption flow
1. User powers on a new device.
2. User opens Alice app.
3. User scans device QR code.
4. App connects locally to the device onboarding interface.
5. App passes network credentials or hub join credentials.
6. Device joins the household network.
7. Device proves identity using the QR token.
8. Hub approves adoption.
9. User names the device and assigns it to a room.
10. Device becomes part of the household state graph.

## 7.2 What the QR code should represent
The QR should map to:
- device class
- unique device ID
- secure pairing secret or signed claim token
- manufacturing batch / revision data optionally

## 7.3 What the app should ask during adoption
- device name
- room assignment
- suggested names
- icon/category
- optional notes
- whether to immediately create an automation

## 7.4 Adoption rules
- no untrusted device gets control rights by discovery alone
- every adopted device belongs to one household
- transfer requires removal or reset
- duplicate claims are rejected

---

## 8. AI assistant model

Alice's assistant is broader than home control.

## 8.1 Assistant scope
The assistant must support:
- home control
- home explanations
- questions and answers
- mathematics
- homework support
- reminders and light productivity
- natural conversation
- household-aware suggestions

## 8.2 Two modes
### AI mode enabled
User gets:
- conversational assistant
- personalised memory
- natural-language home control
- general-purpose reasoning

### AI mode disabled
User still gets:
- room/device control
- scenes
- standard automations
- manual interactions
- template-based routines

## 8.3 Wake word strategy
Short term:
- curated list of supported wake words

Long term:
- user-custom wake words
- legal and product filters to block protected or prohibited names

Default brand experience:
- Alice

## 8.4 First assistant onboarding
If enabled, user should:
- choose assistant voice
- choose assistant wake word from available list
- answer a few lightweight preference prompts
- optionally ask Alice a few sample questions

This helps the product feel alive immediately.

---

## 9. UX philosophy

Alice should feel like:
- premium
- calm
- warm
- competent
- understandable

Alice should not feel like:
- a server admin panel
- a toy
- a hobbyist wiring harness
- a mystery box

## 9.1 UX rules
- state before settings
- rooms before devices
- actions before jargon
- explanations before magic
- confidence before clutter

## 9.2 Setup rules
- essential steps only are mandatory
- everything else can be skipped and revisited
- QR everywhere practical
- avoid passwords on TVs and embedded devices
- phone-assisted pairing is the default

---

## 10. Information architecture

## 10.1 Mobile app primary navigation
Recommended primary tabs:
- Home
- Rooms
- Devices
- Automations
- Alice
- Settings

## 10.2 Home tab
Purpose:
- household snapshot
- important alerts
- suggested actions
- current conditions

## 10.3 Rooms tab
Purpose:
- room-first navigation
- quick controls
- recent room activity
- sensor summaries

## 10.4 Devices tab
Purpose:
- inventory
- status
- pending adoptions
- offline diagnostics

## 10.5 Automations tab
Purpose:
- quick templates
- edit simple rules
- review recent runs

## 10.6 Alice tab
Purpose:
- text and voice conversation
- assistant history
- reasoning/explanations
- non-home help

## 10.7 Settings tab
Purpose:
- household
- privacy
- remote access
- users
- developer tools
- advanced device settings

## 10.8 Web UI
The web UI is not a duplicate of mobile.
It is the advanced surface for:
- deeper automation composition
- debugging
- graph/history views
- large-form editing
- power-user workflows

---

## 11. Remote access philosophy

Remote access is useful, but must not violate local-first principles.

## 11.1 Requirements
- no mandatory port forwarding
- no mandatory public IP
- no mandatory cloud login for local use
- user can disable it fully

## 11.2 Product rule
Remote access must be:
- brokered
- encrypted
- reversible
- clearly disclosed

## 11.3 Future surfaces requiring remote path
- mobile app away from home
- car
- TV outside local context
- other household surfaces
- future companion devices

---

## 12. Founder-defined MVP

This is not a conventional ultra-lean MVP.  
This is better described as an **Alpha Household Pilot** focused on a complete, convincing living room.

## 12.1 MVP goals
The MVP must prove:
- polished local-first setup
- polished native and web UI
- Alice as a real assistant, not just switch control
- a living room that feels complete
- device reuse into most other rooms later

## 12.2 MVP living room scope
The living room MVP includes:

### Core product
- Alice Hub
- mobile app
- web UI
- local account system
- household and room model
- remote access option

### AI and interaction
- conversational Alice assistant
- text chat
- voice chat
- home control
- general knowledge support
- math/homework/help capabilities
- household context awareness

### Living room hardware
- ESP32-based voice assistant satellite module
- blinds controller
- smart light switch
- smart plug/socket control
- TV integration or TV companion path
- temperature/humidity/light sensor
- presence detection

## 12.3 Reusability requirement
The MVP devices should be designed so the same hardware families can be reused in most of the rest of the house with minimal redesign.

---

## 13. Product decisions already locked

The following decisions are treated as current defaults unless deliberately changed:

- Alice is the name.
- It is local-first.
- Mobile is the primary setup path.
- No mandatory cloud signup.
- QR-based hub claim.
- QR-based device adoption.
- House plan is modelled early.
- Occupants include non-app users.
- AI assistant is optional but important.
- Web UI exists for deeper automation work.
- Remote access is brokered, not exposed through router ports.
- The living room is the first complete room.

---

## 14. Product roadmap

## Phase 1 — foundation
- hub claim
- local accounts
- room model
- device adoption
- mobile app core
- web UI core
- logs
- simple automation engine

## Phase 2 — living room pilot
- living room hardware set
- polished native app
- polished web UI
- local relay / remote access option
- assistant conversation loop
- basic general-purpose assistant tools

## Phase 3 — household expansion
- more room types
- more device classes
- household member roles
- better presence and routine understanding

## Phase 4 — broader ecosystem
- TV and custom Android surfaces
- car and wearable surfaces
- developer SDK
- optional cloud extensions
- richer memory and personalization

---

## 15. Product success criteria

Alice is succeeding when:
- setup feels easy and premium
- a normal person can adopt a device without jargon
- the assistant feels useful even when not controlling the home
- the living room can demonstrate a believable end-state product
- the system remains understandable and safe

---

## 16. Open questions

These are deliberate open design questions, not gaps in principle:
- exact local LLM sizing by hub class
- whether TV is a companion box or custom Android fork first
- exact presence-sensing sensor choice for MVP
- exact blind motor hardware strategy
- long-term wake word customisation pipeline
- whether family member setup should include optional roles on day one

---

## 17. Final statement

Alice is not being built as a gadget platform.

It is being built as:
- a private household operating system
- a local intelligence layer
- a virtual butler
- a product users can trust in their real lives
