#include <Arduino.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WebServer.h>
#include <WiFi.h>
#include <cmath>

#include "device_config.h"
#include "secrets.h"

namespace {

using namespace alice::sensor_node;

enum class StatusMode {
  Booting,
  ConnectingWifi,
  ConnectingMqtt,
  Claiming,
  OtaInProgress,
  ConnectedHold,
  Idle,
};

struct RuntimeConfig {
  bool claimed = false;
  String device_id;
  String device_name;
  String model;
  String device_type;
  String fw_version;
  String mqtt_host;
  uint16_t mqtt_port = 0;
  String mqtt_topic_prefix;
  String mqtt_client_id;
  String mqtt_username;
  String mqtt_password;
};

struct SensorCache {
  bool motion_known = false;
  bool motion = false;
  bool published_motion_known = false;
  bool published_motion = false;

  bool temperature_valid = false;
  float temperature_c = 0.0f;
  bool published_temperature_valid = false;
  float published_temperature_c = 0.0f;

  bool light_valid = false;
  int light_raw = 0;
  float light_lux = 0.0f;
  bool published_light_valid = false;
  int published_light_raw = 0;

  unsigned long last_temperature_sample_ms = 0;
  unsigned long last_light_sample_ms = 0;
  unsigned long last_temperature_publish_ms = 0;
  unsigned long last_light_publish_ms = 0;
  unsigned long last_snapshot_publish_ms = 0;
};

Preferences preferences;
WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);
WebServer setup_server(SETUP_SERVER_PORT);
DHT dht(DHT_PIN, DHT11);

RuntimeConfig runtime_config;
SensorCache sensor_cache;
StatusMode status_mode = StatusMode::Booting;
bool status_led_on = false;
unsigned long last_status_toggle_ms = 0;
unsigned long mqtt_connected_at_ms = 0;
unsigned long last_claim_attempt_ms = 0;
unsigned long last_wifi_attempt_ms = 0;
unsigned long scheduled_restart_at_ms = 0;
bool ota_configured = false;
bool setup_ap_started = false;
bool setup_server_started = false;
bool station_connected_logged = false;
String mqtt_host_buffer;

String read_pref_string(const char* key) {
  if (!preferences.isKey(key)) {
    return "";
  }
  return preferences.getString(key, "");
}

void write_pref_string(const char* key, const String& value) {
  preferences.putString(key, value);
}

String effective_device_id() {
  return runtime_config.claimed && runtime_config.device_id.length() > 0 ? runtime_config.device_id : DEVICE_ID;
}

String effective_device_name() {
  return runtime_config.claimed && runtime_config.device_name.length() > 0 ? runtime_config.device_name : DEVICE_NAME;
}

String effective_model() {
  return runtime_config.claimed && runtime_config.model.length() > 0 ? runtime_config.model : DEVICE_MODEL;
}

String effective_device_type() {
  return runtime_config.claimed && runtime_config.device_type.length() > 0 ? runtime_config.device_type : DEVICE_TYPE;
}

String effective_fw_version() {
  return runtime_config.claimed && runtime_config.fw_version.length() > 0 ? runtime_config.fw_version : FW_VERSION;
}

String effective_mqtt_host() {
  return runtime_config.claimed && runtime_config.mqtt_host.length() > 0 ? runtime_config.mqtt_host : MQTT_HOST;
}

uint16_t effective_mqtt_port() {
  return runtime_config.claimed && runtime_config.mqtt_port > 0 ? runtime_config.mqtt_port : MQTT_PORT;
}

String effective_mqtt_topic_prefix() {
  return runtime_config.claimed && runtime_config.mqtt_topic_prefix.length() > 0 ? runtime_config.mqtt_topic_prefix : MQTT_TOPIC_PREFIX;
}

String effective_mqtt_client_id() {
  return runtime_config.claimed && runtime_config.mqtt_client_id.length() > 0 ? runtime_config.mqtt_client_id : effective_device_id();
}

String effective_mqtt_username() {
  return runtime_config.claimed ? runtime_config.mqtt_username : MQTT_USERNAME;
}

String effective_mqtt_password() {
  return runtime_config.claimed ? runtime_config.mqtt_password : MQTT_PASSWORD;
}

String effective_wifi_ssid() {
  const String stored = read_pref_string("wifi_ssid");
  if (stored.length() > 0) {
    return stored;
  }
  if (!runtime_config.claimed) {
    return "";
  }
  return WIFI_SSID;
}

String effective_wifi_password() {
  const String stored = read_pref_string("wifi_pass");
  if (stored.length() > 0) {
    return stored;
  }
  if (!runtime_config.claimed) {
    return "";
  }
  return WIFI_PASSWORD;
}

bool has_station_wifi_credentials() {
  return effective_wifi_ssid().length() > 0;
}

String effective_hub_api_base_url() {
  const String stored = read_pref_string("hub_api_url");
  if (stored.length() > 0) {
    return stored;
  }
  if (!runtime_config.claimed) {
    return "";
  }
  return HUB_API_BASE_URL;
}

String bootstrap_id() {
  const String stored = read_pref_string("prov_boot_id");
  if (stored.length() > 0) {
    return stored;
  }
  return BOOTSTRAP_ID;
}

String claim_token() {
  const String stored = read_pref_string("prov_token");
  if (stored.length() > 0) {
    return stored;
  }
  return CLAIM_TOKEN;
}

bool has_claim_inputs() {
  return bootstrap_id().length() > 0 && claim_token().length() > 0;
}

String setup_ap_ssid() {
  String value = String(SETUP_AP_SSID_PREFIX) + effective_device_id();
  if (value.length() > 31) {
    value.remove(31);
  }
  return value;
}

String topic_for(const char* suffix) {
  String topic = effective_mqtt_topic_prefix();
  topic += "/device/";
  topic += effective_device_id();
  topic += "/";
  topic += suffix;
  return topic;
}

void configure_mqtt_server() {
  mqtt_host_buffer = effective_mqtt_host();
  mqtt_client.setServer(mqtt_host_buffer.c_str(), effective_mqtt_port());
}

void load_runtime_config() {
  preferences.begin("alice", false);
  runtime_config.claimed = preferences.getBool("claimed", false);
  if (!runtime_config.claimed) {
    return;
  }

  runtime_config.device_id = read_pref_string("device_id");
  runtime_config.device_name = read_pref_string("device_name");
  runtime_config.model = read_pref_string("model");
  runtime_config.device_type = read_pref_string("device_type");
  runtime_config.fw_version = read_pref_string("fw_version");
  runtime_config.mqtt_host = read_pref_string("mqtt_host");
  runtime_config.mqtt_port = preferences.getUShort("mqtt_port", MQTT_PORT);
  runtime_config.mqtt_topic_prefix = read_pref_string("topic_prefix");
  runtime_config.mqtt_client_id = read_pref_string("client_id");
  runtime_config.mqtt_username = read_pref_string("mqtt_user");
  runtime_config.mqtt_password = read_pref_string("mqtt_pass");
}

void save_runtime_config() {
  preferences.putBool("claimed", runtime_config.claimed);
  write_pref_string("device_id", runtime_config.device_id);
  write_pref_string("device_name", runtime_config.device_name);
  write_pref_string("model", runtime_config.model);
  write_pref_string("device_type", runtime_config.device_type);
  write_pref_string("fw_version", runtime_config.fw_version);
  write_pref_string("mqtt_host", runtime_config.mqtt_host);
  preferences.putUShort("mqtt_port", runtime_config.mqtt_port);
  write_pref_string("topic_prefix", runtime_config.mqtt_topic_prefix);
  write_pref_string("client_id", runtime_config.mqtt_client_id);
  write_pref_string("mqtt_user", runtime_config.mqtt_username);
  write_pref_string("mqtt_pass", runtime_config.mqtt_password);
}

void clear_claim_inputs() {
  write_pref_string("prov_boot_id", "");
  write_pref_string("prov_token", "");
}

void reset_claimed_runtime() {
  runtime_config = RuntimeConfig{};
  sensor_cache = SensorCache{};
  preferences.clear();
}

void schedule_restart() {
  scheduled_restart_at_ms = millis() + PROVISIONING_RESTART_DELAY_MS;
}

String build_json_string(JsonDocument& doc) {
  String body;
  serializeJson(doc, body);
  return body;
}

void print_device_qr_payload() {
  JsonDocument doc;
  doc["v"] = 1;
  doc["bootstrap_id"] = bootstrap_id();
  doc["setup_code"] = SETUP_CODE;
  doc["model"] = effective_model();
  doc["device_type"] = effective_device_type();
  doc["setup_ap_ssid"] = setup_ap_ssid();
  Serial.println("ALICE_DEVICE_QR");
  serializeJson(doc, Serial);
  Serial.println();
}

void send_setup_json_response(int status_code, JsonDocument& doc) {
  setup_server.sendHeader("Access-Control-Allow-Origin", "*");
  setup_server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  setup_server.send(status_code, "application/json", build_json_string(doc));
}

void handle_setup_preflight() {
  setup_server.sendHeader("Access-Control-Allow-Origin", "*");
  setup_server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  setup_server.send(204);
}

float estimate_lux(int raw_value) {
  float normalized = static_cast<float>(raw_value) / 4095.0f;
  if (LIGHT_SENSOR_INVERTED) {
    normalized = 1.0f - normalized;
  }
  normalized = constrain(normalized, 0.0f, 1.0f);
  return normalized * LIGHT_SENSOR_MAX_LUX;
}

void publish_json(const String& topic, JsonDocument& doc, bool retain = true) {
  char buffer[1024];
  const size_t written = serializeJson(doc, buffer, sizeof(buffer));
  const bool ok = mqtt_client.publish(topic.c_str(), reinterpret_cast<const uint8_t*>(buffer), written, retain);
  Serial.print(ok ? "MQTT publish OK: " : "MQTT publish FAILED: ");
  Serial.print(topic);
  Serial.print(" -> ");
  Serial.println(buffer);
}

void publish_availability(const char* status) {
  mqtt_client.publish(topic_for("availability").c_str(), status, true);
}

void write_status_led(bool on) {
  status_led_on = on;
  const int active = STATUS_LED_ACTIVE_HIGH ? HIGH : LOW;
  const int inactive = STATUS_LED_ACTIVE_HIGH ? LOW : HIGH;
  digitalWrite(STATUS_LED_PIN, on ? active : inactive);
}

void set_status_mode(StatusMode new_mode) {
  if (status_mode == new_mode) {
    return;
  }
  status_mode = new_mode;
  last_status_toggle_ms = millis();
  if (status_mode == StatusMode::ConnectedHold) {
    mqtt_connected_at_ms = millis();
    write_status_led(true);
  } else if (status_mode == StatusMode::Idle) {
    write_status_led(false);
  }
}

uint32_t blink_interval_for(StatusMode mode) {
  switch (mode) {
    case StatusMode::Booting:
      return STATUS_BOOT_BLINK_MS;
    case StatusMode::ConnectingWifi:
      return STATUS_WIFI_BLINK_MS;
    case StatusMode::ConnectingMqtt:
      return STATUS_MQTT_BLINK_MS;
    case StatusMode::Claiming:
      return STATUS_BOOT_BLINK_MS;
    case StatusMode::OtaInProgress:
      return STATUS_BOOT_BLINK_MS;
    case StatusMode::ConnectedHold:
    case StatusMode::Idle:
      return 0;
  }
  return 0;
}

void update_status_led() {
  if (status_mode == StatusMode::ConnectedHold) {
    if (millis() - mqtt_connected_at_ms >= STATUS_CONNECTED_HOLD_MS) {
      set_status_mode(StatusMode::Idle);
    }
    return;
  }

  const uint32_t interval = blink_interval_for(status_mode);
  if (interval == 0) {
    return;
  }

  const unsigned long now = millis();
  if (now - last_status_toggle_ms >= interval) {
    write_status_led(!status_led_on);
    last_status_toggle_ms = now;
  }
}

void print_runtime_config() {
  JsonDocument doc;
  doc["claimed"] = runtime_config.claimed;
  doc["device_id"] = effective_device_id();
  doc["device_name"] = effective_device_name();
  doc["wifi_ssid"] = effective_wifi_ssid();
  doc["hub_api_base_url"] = effective_hub_api_base_url();
  doc["mqtt_host"] = effective_mqtt_host();
  doc["mqtt_port"] = effective_mqtt_port();
  doc["topic_prefix"] = effective_mqtt_topic_prefix();
  doc["mqtt_client_id"] = effective_mqtt_client_id();
  doc["bootstrap_id"] = bootstrap_id();
  doc["has_claim_inputs"] = has_claim_inputs();
  doc["setup_ap_ssid"] = setup_ap_ssid();
  serializeJsonPretty(doc, Serial);
  Serial.println();
}

void reset_publish_tracking() {
  sensor_cache.published_motion_known = false;
  sensor_cache.published_temperature_valid = false;
  sensor_cache.published_light_valid = false;
  sensor_cache.last_temperature_publish_ms = 0;
  sensor_cache.last_light_publish_ms = 0;
  sensor_cache.last_snapshot_publish_ms = 0;
}

bool runtime_ready_for_sensor_loop() {
  return runtime_config.claimed && mqtt_client.connected();
}

void publish_hello() {
  JsonDocument doc;
  doc["name"] = effective_device_name();
  doc["model"] = effective_model();
  doc["device_type"] = effective_device_type();
  doc["protocol"] = "wifi-mqtt";
  doc["fw_version"] = effective_fw_version();

  JsonArray capabilities = doc["capabilities"].to<JsonArray>();

  JsonObject temperature = capabilities.add<JsonObject>();
  temperature["capability_id"] = "temperature";
  temperature["kind"] = "sensor.temperature";
  temperature["name"] = "Temperature";
  temperature["slug"] = "temperature";
  temperature["writable"] = 0;
  temperature["traits"]["unit"] = "C";

  JsonObject illuminance = capabilities.add<JsonObject>();
  illuminance["capability_id"] = "illuminance";
  illuminance["kind"] = "sensor.illuminance";
  illuminance["name"] = "Illuminance";
  illuminance["slug"] = "illuminance";
  illuminance["writable"] = 0;
  illuminance["traits"]["unit"] = "lux";

  JsonObject motion = capabilities.add<JsonObject>();
  motion["capability_id"] = "motion";
  motion["kind"] = "sensor.motion";
  motion["name"] = "Motion";
  motion["slug"] = "motion";
  motion["writable"] = 0;
  motion["traits"].to<JsonObject>();

  publish_json(topic_for("hello"), doc, true);
}

void publish_motion(bool motion_detected) {
  JsonDocument doc;
  doc["capability"] = "motion";
  doc["motion"] = motion_detected;
  publish_json(topic_for("state"), doc, true);
  sensor_cache.published_motion = motion_detected;
  sensor_cache.published_motion_known = true;
}

void publish_temperature(float celsius) {
  JsonDocument doc;
  doc["capability"] = "temperature";
  const float rounded_celsius = roundf(celsius * 10.0f) / 10.0f;
  doc["celsius"] = rounded_celsius;
  publish_json(topic_for("state"), doc, true);
  sensor_cache.published_temperature_c = rounded_celsius;
  sensor_cache.published_temperature_valid = true;
  sensor_cache.last_temperature_publish_ms = millis();
}

void publish_illuminance(int raw_value, float lux) {
  JsonDocument doc;
  doc["capability"] = "illuminance";
  doc["raw"] = raw_value;
  doc["lux"] = roundf(lux * 10.0f) / 10.0f;
  publish_json(topic_for("state"), doc, true);
  sensor_cache.published_light_raw = raw_value;
  sensor_cache.published_light_valid = true;
  sensor_cache.last_light_publish_ms = millis();
}

void sample_motion() {
  sensor_cache.motion = digitalRead(PIR_PIN) == HIGH;
  sensor_cache.motion_known = true;
}

void sample_temperature_if_due() {
  const unsigned long now = millis();
  if (sensor_cache.last_temperature_sample_ms != 0 &&
      now - sensor_cache.last_temperature_sample_ms < TEMPERATURE_SAMPLE_INTERVAL_MS) {
    return;
  }

  sensor_cache.last_temperature_sample_ms = now;
  const float temperature_c = dht.readTemperature();
  if (isnan(temperature_c)) {
    Serial.println("DHT11 read failed");
    sensor_cache.temperature_valid = false;
    return;
  }

  sensor_cache.temperature_valid = true;
  sensor_cache.temperature_c = roundf(temperature_c * 10.0f) / 10.0f;
}

void sample_light_if_due() {
  const unsigned long now = millis();
  if (sensor_cache.last_light_sample_ms != 0 &&
      now - sensor_cache.last_light_sample_ms < LIGHT_SAMPLE_INTERVAL_MS) {
    return;
  }

  sensor_cache.last_light_sample_ms = now;
  sensor_cache.light_raw = analogRead(LIGHT_SENSOR_PIN);
  sensor_cache.light_lux = estimate_lux(sensor_cache.light_raw);
  sensor_cache.light_valid = true;
}

bool should_publish_temperature_event() {
  if (!sensor_cache.temperature_valid) {
    return false;
  }
  if (!sensor_cache.published_temperature_valid) {
    return true;
  }
  if (millis() - sensor_cache.last_temperature_publish_ms < SENSOR_EVENT_MIN_INTERVAL_MS) {
    return false;
  }
  return fabsf(sensor_cache.temperature_c - sensor_cache.published_temperature_c) >= TEMPERATURE_EVENT_DELTA_C;
}

bool should_publish_light_event() {
  if (!sensor_cache.light_valid) {
    return false;
  }
  if (!sensor_cache.published_light_valid) {
    return true;
  }
  if (millis() - sensor_cache.last_light_publish_ms < SENSOR_EVENT_MIN_INTERVAL_MS) {
    return false;
  }
  return abs(sensor_cache.light_raw - sensor_cache.published_light_raw) >= LIGHT_EVENT_DELTA_RAW;
}

void publish_motion_on_change() {
  if (!mqtt_client.connected() || !sensor_cache.motion_known) {
    return;
  }
  if (!sensor_cache.published_motion_known || sensor_cache.motion != sensor_cache.published_motion) {
    publish_motion(sensor_cache.motion);
    Serial.println("Motion edge detected, published immediately");
  }
}

void publish_sensor_events() {
  if (!mqtt_client.connected()) {
    return;
  }

  if (should_publish_temperature_event()) {
    publish_temperature(sensor_cache.temperature_c);
    Serial.println("Temperature delta threshold crossed, published immediately");
  }

  if (should_publish_light_event()) {
    publish_illuminance(sensor_cache.light_raw, sensor_cache.light_lux);
    Serial.println("Light delta threshold crossed, published immediately");
  }
}

void publish_snapshot_if_due() {
  if (!mqtt_client.connected()) {
    return;
  }

  const unsigned long now = millis();
  if (sensor_cache.last_snapshot_publish_ms != 0 &&
      now - sensor_cache.last_snapshot_publish_ms < SENSOR_PUBLISH_INTERVAL_MS) {
    return;
  }

  if (sensor_cache.motion_known) {
    publish_motion(sensor_cache.motion);
  }
  if (sensor_cache.temperature_valid) {
    publish_temperature(sensor_cache.temperature_c);
  }
  if (sensor_cache.light_valid) {
    publish_illuminance(sensor_cache.light_raw, sensor_cache.light_lux);
  }

  sensor_cache.last_snapshot_publish_ms = now;
}

void ensure_setup_access_point() {
  if (runtime_config.claimed) {
    if (setup_ap_started) {
      WiFi.softAPdisconnect(true);
      setup_ap_started = false;
    }
    return;
  }

  if (setup_ap_started) {
    return;
  }

  WiFi.mode(WIFI_AP_STA);
  const String ssid = setup_ap_ssid();
  const bool ok = strlen(SETUP_AP_PASSWORD) >= 8 ? WiFi.softAP(ssid.c_str(), SETUP_AP_PASSWORD) : WiFi.softAP(ssid.c_str());
  if (!ok) {
    Serial.println("Failed to start setup AP");
    return;
  }

  setup_ap_started = true;
  Serial.print("Setup AP ready: ");
  Serial.print(ssid);
  Serial.print(" -> ");
  Serial.println(WiFi.softAPIP());
}

void handle_setup_status() {
  JsonDocument doc;
  doc["claimed"] = runtime_config.claimed;
  doc["device_id"] = effective_device_id();
  doc["device_name"] = effective_device_name();
  doc["bootstrap_id"] = bootstrap_id();
  doc["has_claim_inputs"] = has_claim_inputs();
  doc["setup_ap_ssid"] = setup_ap_ssid();
  doc["setup_ap_ip"] = WiFi.softAPIP().toString();
  doc["station_connected"] = WiFi.status() == WL_CONNECTED;
  doc["station_ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "";
  doc["wifi_ssid"] = effective_wifi_ssid();
  doc["hub_api_base_url"] = effective_hub_api_base_url();
  send_setup_json_response(200, doc);
}

void handle_setup_provision() {
  JsonDocument response;
  if (!setup_server.hasArg("plain")) {
    response["detail"] = "Missing JSON body.";
    send_setup_json_response(400, response);
    return;
  }

  JsonDocument request;
  if (deserializeJson(request, setup_server.arg("plain"))) {
    response["detail"] = "Invalid JSON payload.";
    send_setup_json_response(400, response);
    return;
  }

  const char* boot_id = request["bootstrap_id"] | "";
  const char* token = request["claim_token"] | "";
  const char* wifi_ssid = request["wifi_ssid"] | "";
  const char* wifi_password = request["wifi_password"] | "";
  const char* hub_api_base_url = request["hub_api_base_url"] | "";

  if (strlen(boot_id) == 0 || strlen(token) == 0) {
    response["detail"] = "bootstrap_id and claim_token are required.";
    send_setup_json_response(400, response);
    return;
  }

  if (strlen(wifi_ssid) == 0 && !has_station_wifi_credentials()) {
    response["detail"] = "wifi_ssid is required when the device has no saved station credentials.";
    send_setup_json_response(400, response);
    return;
  }

  write_pref_string("prov_boot_id", boot_id);
  write_pref_string("prov_token", token);
  if (strlen(wifi_ssid) > 0) {
    write_pref_string("wifi_ssid", wifi_ssid);
  }
  if (request["wifi_password"].is<const char*>()) {
    write_pref_string("wifi_pass", wifi_password);
  }
  if (strlen(hub_api_base_url) > 0) {
    write_pref_string("hub_api_url", hub_api_base_url);
  }

  response["accepted"] = true;
  response["restart_scheduled"] = true;
  response["bootstrap_id"] = boot_id;
  response["setup_ap_ssid"] = setup_ap_ssid();
  send_setup_json_response(202, response);
  Serial.println("Accepted local provisioning payload, reboot scheduled");
  schedule_restart();
}

void ensure_setup_server() {
  if (runtime_config.claimed || setup_server_started) {
    return;
  }

  setup_server.on("/status", HTTP_GET, handle_setup_status);
  setup_server.on("/status", HTTP_OPTIONS, handle_setup_preflight);
  setup_server.on("/provision", HTTP_POST, handle_setup_provision);
  setup_server.on("/provision", HTTP_OPTIONS, handle_setup_preflight);
  setup_server.begin();
  setup_server_started = true;
  Serial.print("Setup server ready on http://");
  Serial.print(WiFi.softAPIP());
  Serial.print(":");
  Serial.println(SETUP_SERVER_PORT);
}

void connect_wifi() {
  if (!has_station_wifi_credentials()) {
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!station_connected_logged) {
      Serial.print("WiFi connected, IP: ");
      Serial.println(WiFi.localIP());
      station_connected_logged = true;
    }
    return;
  }

  station_connected_logged = false;
  if (millis() - last_wifi_attempt_ms < WIFI_RECONNECT_DELAY_MS) {
    return;
  }

  const String hostname = effective_device_id();
  const String ssid = effective_wifi_ssid();
  const String password = effective_wifi_password();

  set_status_mode(StatusMode::ConnectingWifi);
  WiFi.mode(runtime_config.claimed ? WIFI_STA : WIFI_AP_STA);
  WiFi.setHostname(hostname.c_str());
  WiFi.begin(ssid.c_str(), password.c_str());
  last_wifi_attempt_ms = millis();
  Serial.print("Connecting WiFi to ");
  Serial.println(ssid);
}

void configure_ota() {
  const String hostname = effective_device_id();
  ArduinoOTA.setHostname(hostname.c_str());
  ArduinoOTA.setPort(OTA_PORT);
  if (strlen(OTA_PASSWORD) > 0) {
    ArduinoOTA.setPassword(OTA_PASSWORD);
  }

  ArduinoOTA.onStart([]() {
    set_status_mode(StatusMode::OtaInProgress);
    Serial.println("OTA update starting");
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned int last_percent = 0;
    const unsigned int percent = total == 0 ? 0 : static_cast<unsigned int>((progress * 100U) / total);
    if (percent >= last_percent + 10U || percent == 100U) {
      last_percent = percent;
      Serial.print("OTA progress ");
      Serial.print(percent);
      Serial.println("%");
    }
  });

  ArduinoOTA.onEnd([]() {
    Serial.println("OTA update complete");
    set_status_mode(StatusMode::ConnectedHold);
  });

  ArduinoOTA.onError([](ota_error_t error) {
    Serial.print("OTA error ");
    Serial.println(static_cast<int>(error));
    set_status_mode(StatusMode::ConnectedHold);
  });

  ArduinoOTA.begin();
  Serial.print("Arduino OTA ready on ");
  Serial.print(WiFi.localIP());
  Serial.print(":");
  Serial.println(OTA_PORT);
  ota_configured = true;
}

void ensure_ota() {
  if (ota_configured || WiFi.status() != WL_CONNECTED) {
    return;
  }
  configure_ota();
}

void ensure_mqtt() {
  if (WiFi.status() != WL_CONNECTED || mqtt_client.connected()) {
    return;
  }

  set_status_mode(StatusMode::ConnectingMqtt);
  Serial.print("Connecting MQTT...");

  const String client_id = effective_mqtt_client_id();
  const String username = effective_mqtt_username();
  const String password = effective_mqtt_password();
  const String availability_topic = topic_for("availability");

  bool connected = false;
  if (username.length() == 0) {
    connected = mqtt_client.connect(
        client_id.c_str(),
        nullptr,
        nullptr,
        availability_topic.c_str(),
        1,
        true,
        "offline");
  } else {
    connected = mqtt_client.connect(
        client_id.c_str(),
        username.c_str(),
        password.c_str(),
        availability_topic.c_str(),
        1,
        true,
        "offline");
  }

  if (!connected) {
    Serial.print("failed rc=");
    Serial.println(mqtt_client.state());
    return;
  }

  Serial.println("connected");
  publish_availability("online");
  publish_hello();
  reset_publish_tracking();
  set_status_mode(StatusMode::ConnectedHold);
}

void attempt_claim_if_needed() {
  if (runtime_config.claimed || !has_claim_inputs() || WiFi.status() != WL_CONNECTED) {
    return;
  }
  if (millis() - last_claim_attempt_ms < 10000U) {
    return;
  }

  const String hub_api_base_url = effective_hub_api_base_url();
  if (hub_api_base_url.length() == 0) {
    Serial.println("Cannot claim without a hub_api_base_url");
    return;
  }

  last_claim_attempt_ms = millis();
  set_status_mode(StatusMode::Claiming);
  Serial.println("Attempting provisioning claim completion");

  HTTPClient http;
  const String url = hub_api_base_url + "/provisioning/claim/complete";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  JsonDocument request;
  request["bootstrap_id"] = bootstrap_id();
  request["claim_token"] = claim_token();
  request["fw_version"] = FW_VERSION;
  request["protocol"] = "wifi-mqtt";

  String request_body;
  serializeJson(request, request_body);
  const int status_code = http.POST(request_body);
  const String response_body = http.getString();
  http.end();

  if (status_code != 200) {
    Serial.print("Provisioning claim failed: ");
    Serial.print(status_code);
    Serial.print(" -> ");
    Serial.println(response_body);
    set_status_mode(StatusMode::ConnectingWifi);
    return;
  }

  JsonDocument response;
  if (deserializeJson(response, response_body)) {
    Serial.println("Provisioning claim returned invalid JSON");
    set_status_mode(StatusMode::ConnectingWifi);
    return;
  }

  runtime_config.claimed = true;
  runtime_config.device_id = String(static_cast<const char*>(response["device_id"] | DEVICE_ID));
  runtime_config.device_name = String(static_cast<const char*>(response["device_name"] | DEVICE_NAME));
  runtime_config.model = String(static_cast<const char*>(response["model"] | DEVICE_MODEL));
  runtime_config.device_type = String(static_cast<const char*>(response["device_type"] | DEVICE_TYPE));
  runtime_config.fw_version = String(static_cast<const char*>(response["fw_version"] | FW_VERSION));
  runtime_config.mqtt_host = String(static_cast<const char*>(response["mqtt_host"] | MQTT_HOST));
  runtime_config.mqtt_port = static_cast<uint16_t>(response["mqtt_port"] | MQTT_PORT);
  runtime_config.mqtt_topic_prefix = String(static_cast<const char*>(response["mqtt_topic_prefix"] | MQTT_TOPIC_PREFIX));
  runtime_config.mqtt_client_id = String(static_cast<const char*>(response["mqtt_client_id"] | DEVICE_ID));
  runtime_config.mqtt_username = String(static_cast<const char*>(response["mqtt_username"] | ""));
  runtime_config.mqtt_password = String(static_cast<const char*>(response["mqtt_password"] | ""));
  save_runtime_config();
  clear_claim_inputs();

  Serial.println("Provisioning claim completed, rebooting into claimed runtime");
  delay(500);
  ESP.restart();
}

void handle_serial_provision_payload(const String& payload) {
  JsonDocument doc;
  if (deserializeJson(doc, payload)) {
    Serial.println("Invalid PROVISION payload");
    return;
  }

  const char* boot_id = doc["bootstrap_id"] | "";
  const char* token = doc["claim_token"] | "";
  if (strlen(boot_id) == 0 || strlen(token) == 0) {
    Serial.println("PROVISION requires bootstrap_id and claim_token");
    return;
  }

  write_pref_string("prov_boot_id", boot_id);
  write_pref_string("prov_token", token);
  if (doc["wifi_ssid"].is<const char*>()) {
    write_pref_string("wifi_ssid", doc["wifi_ssid"].as<const char*>());
  }
  if (doc["wifi_password"].is<const char*>()) {
    write_pref_string("wifi_pass", doc["wifi_password"].as<const char*>());
  }
  if (doc["hub_api_base_url"].is<const char*>()) {
    write_pref_string("hub_api_url", doc["hub_api_base_url"].as<const char*>());
  }
  Serial.println("Stored provisioning inputs, restart scheduled");
  schedule_restart();
}

void handle_serial_commands() {
  if (!Serial.available()) {
    return;
  }

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) {
    return;
  }

  if (line == "PRINT_CONFIG") {
    print_runtime_config();
    return;
  }

  if (line == "PRINT_QR") {
    print_device_qr_payload();
    return;
  }

  if (line == "RESET_PROVISIONING") {
    Serial.println("Clearing persisted provisioning state");
    reset_claimed_runtime();
    delay(250);
    ESP.restart();
    return;
  }

  if (!line.startsWith("PROVISION ")) {
    Serial.println("Unknown serial command");
    return;
  }

  handle_serial_provision_payload(line.substring(String("PROVISION ").length()));
}

void handle_scheduled_restart() {
  if (scheduled_restart_at_ms == 0 || millis() < scheduled_restart_at_ms) {
    return;
  }
  Serial.println("Restarting into updated provisioning configuration");
  delay(100);
  ESP.restart();
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(1000);
  Serial.println();
  Serial.println("Alice ESP32 sensor node starting");

  load_runtime_config();

  pinMode(STATUS_LED_PIN, OUTPUT);
  write_status_led(false);
  set_status_mode(StatusMode::Booting);
  pinMode(PIR_PIN, INPUT);
  analogReadResolution(12);
  dht.begin();

  sample_motion();
  sensor_cache.last_temperature_sample_ms = millis() - TEMPERATURE_SAMPLE_INTERVAL_MS;
  sensor_cache.last_light_sample_ms = millis() - LIGHT_SAMPLE_INTERVAL_MS;

  mqtt_client.setBufferSize(2048);
  mqtt_client.setKeepAlive(60);
  WiFi.setSleep(false);

  configure_mqtt_server();
  ensure_setup_access_point();
  ensure_setup_server();
  connect_wifi();
  ensure_ota();
  print_runtime_config();
  if (!runtime_config.claimed) {
    print_device_qr_payload();
  }
}

void loop() {
  handle_serial_commands();
  handle_scheduled_restart();

  ensure_setup_access_point();
  ensure_setup_server();
  if (!runtime_config.claimed) {
    setup_server.handleClient();
  }

  connect_wifi();
  ensure_ota();
  attempt_claim_if_needed();
  if (ota_configured) {
    ArduinoOTA.handle();
  }
  ensure_mqtt();
  mqtt_client.loop();
  update_status_led();

  if (runtime_ready_for_sensor_loop()) {
    sample_motion();
    sample_temperature_if_due();
    sample_light_if_due();

    publish_motion_on_change();
    publish_sensor_events();
    publish_snapshot_if_due();
  }

  delay(50);
}
