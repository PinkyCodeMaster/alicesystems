#pragma once

#include <Arduino.h>

namespace alice::relay_node {

static constexpr uint32_t SERIAL_BAUD_RATE = 115200;

static constexpr int OUTPUT_PIN = 2;
static constexpr bool OUTPUT_ACTIVE_HIGH = true;

static constexpr uint32_t MQTT_RECONNECT_DELAY_MS = 5000;
static constexpr uint32_t STATE_PUBLISH_INTERVAL_MS = 30000;

}  // namespace alice::relay_node
