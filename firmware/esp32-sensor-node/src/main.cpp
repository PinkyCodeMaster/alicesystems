#include <Arduino.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <cmath>
#include <DHT.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "device_config.h"
#include "secrets.h"

namespace {

using namespace alice::sensor_node;

WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);
DHT dht(DHT_PIN, DHT11);

unsigned long last_publish_ms = 0;
unsigned long mqtt_connected_at_ms = 0;
unsigned long last_temperature_publish_ms = 0;
unsigned long last_light_publish_ms = 0;
bool last_motion_state = false;
bool motion_state_known = false;
float last_published_temperature_c = NAN;
int last_published_light_raw = -1;

enum class StatusMode {
  Booting,
  ConnectingWifi,
  ConnectingMqtt,
  OtaInProgress,
  ConnectedHold,
  Idle,
};

StatusMode status_mode = StatusMode::Booting;
bool status_led_on = false;
unsigned long last_status_toggle_ms = 0;

String topic_for(const char* suffix) {
  String topic = MQTT_TOPIC_PREFIX;
  topic += "/device/";
  topic += DEVICE_ID;
  topic += "/";
  topic += suffix;
  return topic;
}

float estimate_lux(int raw_value) {
  float normalized = static_cast<float>(raw_value) / 4095.0f;
  if (LIGHT_SENSOR_INVERTED) {
    normalized = 1.0f - normalized;
  }
  if (normalized < 0.0f) {
    normalized = 0.0f;
  }
  if (normalized > 1.0f) {
    normalized = 1.0f;
  }
  return normalized * LIGHT_SENSOR_MAX_LUX;
}

void publish_json(const String& topic, JsonDocument& doc, bool retain = true) {
  char buffer[1024];
  size_t written = serializeJson(doc, buffer, sizeof(buffer));
  bool ok = mqtt_client.publish(topic.c_str(), reinterpret_cast<const uint8_t*>(buffer), written, retain);
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
  int active = STATUS_LED_ACTIVE_HIGH ? HIGH : LOW;
  int inactive = STATUS_LED_ACTIVE_HIGH ? LOW : HIGH;
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

  uint32_t interval = blink_interval_for(status_mode);
  if (interval == 0) {
    return;
  }

  unsigned long now = millis();
  if (now - last_status_toggle_ms >= interval) {
    write_status_led(!status_led_on);
    last_status_toggle_ms = now;
  }
}

void publish_hello() {
  JsonDocument doc;
  doc["name"] = DEVICE_NAME;
  doc["model"] = DEVICE_MODEL;
  doc["device_type"] = DEVICE_TYPE;
  doc["protocol"] = "wifi-mqtt";
  doc["fw_version"] = FW_VERSION;

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

void publish_temperature(float celsius) {
  JsonDocument doc;
  doc["capability"] = "temperature";
  float rounded_celsius = roundf(celsius * 10.0f) / 10.0f;
  doc["celsius"] = rounded_celsius;
  publish_json(topic_for("state"), doc, true);
  last_published_temperature_c = rounded_celsius;
  last_temperature_publish_ms = millis();
}

void publish_illuminance(int raw_value) {
  JsonDocument doc;
  doc["capability"] = "illuminance";
  doc["raw"] = raw_value;
  doc["lux"] = roundf(estimate_lux(raw_value) * 10.0f) / 10.0f;
  publish_json(topic_for("state"), doc, true);
  last_published_light_raw = raw_value;
  last_light_publish_ms = millis();
}

void publish_motion(bool motion_detected) {
  JsonDocument doc;
  doc["capability"] = "motion";
  doc["motion"] = motion_detected;
  publish_json(topic_for("state"), doc, true);
}

bool should_publish_temperature(float temperature_c, bool force_snapshot) {
  if (isnan(temperature_c)) {
    return false;
  }
  if (force_snapshot || isnan(last_published_temperature_c)) {
    return true;
  }
  if (millis() - last_temperature_publish_ms < SENSOR_EVENT_MIN_INTERVAL_MS) {
    return false;
  }
  return fabsf(temperature_c - last_published_temperature_c) >= TEMPERATURE_EVENT_DELTA_C;
}

bool should_publish_light(int raw_light, bool force_snapshot) {
  if (force_snapshot || last_published_light_raw < 0) {
    return true;
  }
  if (millis() - last_light_publish_ms < SENSOR_EVENT_MIN_INTERVAL_MS) {
    return false;
  }
  return abs(raw_light - last_published_light_raw) >= LIGHT_EVENT_DELTA_RAW;
}

void connect_wifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  set_status_mode(StatusMode::ConnectingWifi);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(DEVICE_ID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    update_status_led();
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("WiFi connected, IP: ");
  Serial.println(WiFi.localIP());
}

void configure_ota() {
  ArduinoOTA.setHostname(DEVICE_ID);
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
    unsigned int percent = total == 0 ? 0 : static_cast<unsigned int>((progress * 100U) / total);
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
}

void ensure_mqtt() {
  if (mqtt_client.connected()) {
    return;
  }

  set_status_mode(StatusMode::ConnectingMqtt);
  while (!mqtt_client.connected()) {
    Serial.print("Connecting MQTT...");

    bool connected = false;
    if (strlen(MQTT_USERNAME) == 0) {
      connected = mqtt_client.connect(
          DEVICE_ID,
          nullptr,
          nullptr,
          topic_for("availability").c_str(),
          1,
          true,
          "offline");
    } else {
      connected = mqtt_client.connect(
          DEVICE_ID,
          MQTT_USERNAME,
          MQTT_PASSWORD,
          topic_for("availability").c_str(),
          1,
          true,
          "offline");
    }

    if (connected) {
      Serial.println("connected");
      publish_availability("online");
      publish_hello();
      last_publish_ms = 0;
      last_temperature_publish_ms = 0;
      last_light_publish_ms = 0;
      last_published_temperature_c = NAN;
      last_published_light_raw = -1;
      set_status_mode(StatusMode::ConnectedHold);
    } else {
      Serial.print("failed rc=");
      Serial.print(mqtt_client.state());
      Serial.println(", retrying");
      update_status_led();
      delay(MQTT_RECONNECT_DELAY_MS);
    }
  }
}

void publish_sensor_snapshot(bool force_snapshot) {
  float temperature_c = dht.readTemperature();
  if (should_publish_temperature(temperature_c, force_snapshot)) {
    publish_temperature(temperature_c);
    if (!force_snapshot) {
      Serial.println("Temperature delta threshold crossed, published immediately");
    }
  } else if (isnan(temperature_c)) {
    Serial.println("DHT11 read failed");
  }

  int raw_light = analogRead(LIGHT_SENSOR_PIN);
  if (should_publish_light(raw_light, force_snapshot)) {
    publish_illuminance(raw_light);
    if (!force_snapshot) {
      Serial.println("Light delta threshold crossed, published immediately");
    }
  }

  bool motion_detected = digitalRead(PIR_PIN) == HIGH;
  if (force_snapshot || !motion_state_known) {
    publish_motion(motion_detected);
    last_motion_state = motion_detected;
    motion_state_known = true;
  }
}

void handle_motion_edge() {
  bool motion_detected = digitalRead(PIR_PIN) == HIGH;
  if (!motion_state_known || motion_detected != last_motion_state) {
    publish_motion(motion_detected);
    last_motion_state = motion_detected;
    motion_state_known = true;
    Serial.println("Motion edge detected, published immediately");
  }
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(1000);
  Serial.println();
  Serial.println("Alice ESP32 sensor node starting");

  pinMode(STATUS_LED_PIN, OUTPUT);
  write_status_led(false);
  set_status_mode(StatusMode::Booting);
  pinMode(PIR_PIN, INPUT);
  analogReadResolution(12);
  dht.begin();

  mqtt_client.setServer(MQTT_HOST, MQTT_PORT);
  mqtt_client.setBufferSize(2048);
  mqtt_client.setKeepAlive(60);
  WiFi.setSleep(false);

  connect_wifi();
  configure_ota();
}

void loop() {
  connect_wifi();
  ArduinoOTA.handle();
  ensure_mqtt();
  mqtt_client.loop();
  update_status_led();

  handle_motion_edge();
  publish_sensor_snapshot(false);

  unsigned long now = millis();
  if (last_publish_ms == 0 || now - last_publish_ms >= SENSOR_PUBLISH_INTERVAL_MS) {
    publish_sensor_snapshot(true);
    last_publish_ms = now;
  }

  delay(50);
}
