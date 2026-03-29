# Practice Stack

This stack is a rehearsal environment for:

- first-run hub setup
- browser and mobile access over the LAN
- claiming two simulated devices into Home OS

It is intentionally a practice rig, not a production packaging path.

## What It Starts

- `hub-api`
- `assistant-runtime`
- `web-dashboard`
- Mosquitto
- one mock sensor device
- one mock relay device

All services share a dedicated Docker bridge network with static internal IPs.

## Published Host Ports

- dashboard: `3000`
- hub API: `8000`
- assistant: `8010`
- broker: `1883`
- mock sensor setup endpoint: `48081`
- mock relay setup endpoint: `48082`

## Seeded Practice Devices

The hub container seeds these bootstrap records on startup:

- `boot_mock_sensor_01` with setup code `482913`
- `boot_mock_relay_01` with setup code `918274`

The claimed device IDs are:

- `dev_mock_sensor_01`
- `dev_mock_relay_01`

## Practice Flow

1. Start the stack.
2. Open `http://<host-ip>:3000`.
3. Complete first-run hub setup in the dashboard.
4. In the mobile app, point the API base URL at `http://<host-ip>:8000/api/v1`.
5. Open the `Onboard` tab and start a claim session for one of the seeded bootstrap IDs.
6. Use manual device handoff with:
   - sensor setup URL: `http://<host-ip>:48081`
   - relay setup URL: `http://<host-ip>:48082`
7. Watch the claimed devices appear in the dashboard.

## Notes

- The dashboard is the current hub onboarding UI.
- Device claiming is currently exposed in the mobile app, not the web dashboard.
- The mock devices accept the existing `/provision` payload used by the mobile onboarding flow.
- The mock relay subscribes to command topics and publishes command acknowledgements.
