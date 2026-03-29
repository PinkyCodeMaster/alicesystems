#pragma once

#include <Arduino.h>

namespace alice::sensor_node {

static constexpr uint32_t SERIAL_BAUD_RATE = 115200;

static constexpr gpio_num_t LIGHT_SENSOR_PIN = GPIO_NUM_34;
static constexpr int DHT_PIN = 26;
static constexpr int PIR_PIN = 27;
static constexpr int STATUS_LED_PIN = 2;
static constexpr bool STATUS_LED_ACTIVE_HIGH = true;

static constexpr uint32_t SENSOR_PUBLISH_INTERVAL_MS = 15000;
static constexpr uint32_t TEMPERATURE_SAMPLE_INTERVAL_MS = 2500;
static constexpr uint32_t LIGHT_SAMPLE_INTERVAL_MS = 500;
static constexpr uint32_t SENSOR_EVENT_MIN_INTERVAL_MS = 1000;
static constexpr uint32_t MQTT_RECONNECT_DELAY_MS = 5000;
static constexpr uint32_t WIFI_RECONNECT_DELAY_MS = 5000;
static constexpr uint32_t STATUS_BOOT_BLINK_MS = 150;
static constexpr uint32_t STATUS_WIFI_BLINK_MS = 300;
static constexpr uint32_t STATUS_MQTT_BLINK_MS = 600;
static constexpr uint32_t STATUS_CONNECTED_HOLD_MS = 120000;
static constexpr uint16_t SETUP_SERVER_PORT = 80;
static constexpr char SETUP_AP_SSID_PREFIX[] = "AliceSetup-";
static constexpr char SETUP_AP_PASSWORD[] = "alice-setup";
static constexpr uint32_t PROVISIONING_RESTART_DELAY_MS = 1200;

static constexpr bool LIGHT_SENSOR_INVERTED = false;
static constexpr float LIGHT_SENSOR_MAX_LUX = 1000.0f;
static constexpr float TEMPERATURE_EVENT_DELTA_C = 0.3f;
static constexpr int LIGHT_EVENT_DELTA_RAW = 200;

}  // namespace alice::sensor_node
