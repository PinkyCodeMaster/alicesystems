#pragma once

#include <Arduino.h>

namespace alice::relay_node {

static constexpr uint32_t SERIAL_BAUD_RATE = 115200;

static constexpr int OUTPUT_PIN = 2;
static constexpr bool OUTPUT_ACTIVE_HIGH = true;

static constexpr uint32_t MQTT_RECONNECT_DELAY_MS = 5000;
static constexpr uint32_t WIFI_RECONNECT_DELAY_MS = 5000;
static constexpr uint32_t STATE_PUBLISH_INTERVAL_MS = 30000;
static constexpr uint16_t SETUP_SERVER_PORT = 80;
static constexpr char SETUP_AP_SSID_PREFIX[] = "AliceSetup-";
static constexpr char SETUP_AP_PASSWORD[] = "alice-setup";
static constexpr uint32_t PROVISIONING_RESTART_DELAY_MS = 1200;

}  // namespace alice::relay_node
