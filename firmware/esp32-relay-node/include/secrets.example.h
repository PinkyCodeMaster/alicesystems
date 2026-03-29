#pragma once

namespace alice::relay_node {

static constexpr char WIFI_SSID[] = "YOUR_WIFI_SSID";
static constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";

static constexpr char MQTT_HOST[] = "192.168.1.10";
static constexpr uint16_t MQTT_PORT = 1883;
static constexpr char MQTT_USERNAME[] = "";
static constexpr char MQTT_PASSWORD[] = "";
static constexpr char MQTT_TOPIC_PREFIX[] = "alice/v1";
static constexpr char HUB_API_BASE_URL[] = "http://192.168.0.29:8000/api/v1";
static constexpr uint16_t OTA_PORT = 3232;
static constexpr char OTA_PASSWORD[] = "";
static constexpr char BOOTSTRAP_ID[] = "";
static constexpr char SETUP_CODE[] = "";
static constexpr char CLAIM_TOKEN[] = "";

static constexpr char DEVICE_ID[] = "dev_light_bench_01";
static constexpr char DEVICE_NAME[] = "Bench Light";
static constexpr char DEVICE_MODEL[] = "alice.relay.r1";
static constexpr char DEVICE_TYPE[] = "relay_node";
static constexpr char FW_VERSION[] = "0.1.1";

}  // namespace alice::relay_node
