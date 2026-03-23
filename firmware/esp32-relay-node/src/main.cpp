#include <Arduino.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "device_config.h"
#include "secrets.h"

namespace {

using namespace alice::relay_node;

WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);
bool relay_on = false;
unsigned long last_state_publish_ms = 0;

String topic_for(const char* suffix) {
  String topic = MQTT_TOPIC_PREFIX;
  topic += "/device/";
  topic += DEVICE_ID;
  topic += "/";
  topic += suffix;
  return topic;
}

void apply_output(bool on) {
  relay_on = on;
  int level = relay_on == OUTPUT_ACTIVE_HIGH ? HIGH : LOW;
  int opposite = OUTPUT_ACTIVE_HIGH ? LOW : HIGH;
  digitalWrite(OUTPUT_PIN, relay_on ? level : opposite);
}

void publish_json(const String& topic, JsonDocument& doc, bool retain = true) {
  char buffer[512];
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

void publish_hello() {
  JsonDocument doc;
  doc["name"] = DEVICE_NAME;
  doc["model"] = DEVICE_MODEL;
  doc["device_type"] = DEVICE_TYPE;
  doc["protocol"] = "wifi-mqtt";
  doc["fw_version"] = FW_VERSION;

  JsonArray capabilities = doc["capabilities"].to<JsonArray>();
  JsonObject relay = capabilities.add<JsonObject>();
  relay["capability_id"] = "relay";
  relay["kind"] = "switch.relay";
  relay["name"] = "Light";
  relay["slug"] = "light";
  relay["writable"] = 1;
  relay["traits"].to<JsonObject>();

  publish_json(topic_for("hello"), doc, true);
}

void publish_state() {
  JsonDocument doc;
  doc["capability"] = "relay";
  doc["on"] = relay_on;
  publish_json(topic_for("state"), doc, true);
  last_state_publish_ms = millis();
}

void publish_ack(const JsonDocument& command_doc) {
  JsonDocument doc;
  doc["cmd_id"] = command_doc["cmd_id"] | "";
  doc["target_entity_id"] = command_doc["target_entity_id"] | "";
  doc["status"] = "applied";
  doc["name"] = command_doc["name"] | "";
  doc["params"] = command_doc["params"];
  doc["state"]["on"] = relay_on;
  publish_json(topic_for("ack"), doc, false);
}

void handle_command(const byte* payload, unsigned int length) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    Serial.println("Invalid JSON command");
    return;
  }

  const char* type = doc["type"] | "";
  const char* name = doc["name"] | "";
  if (strcmp(type, "entity.command") != 0 || strcmp(name, "switch.set") != 0) {
    Serial.println("Ignoring unsupported command");
    return;
  }

  if (!doc["params"]["on"].is<bool>()) {
    Serial.println("Ignoring command without params.on");
    return;
  }

  bool requested_on = doc["params"]["on"].as<bool>();
  apply_output(requested_on);
  publish_state();
  publish_ack(doc);
  Serial.print("Relay set to ");
  Serial.println(relay_on ? "ON" : "OFF");
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT message on ");
  Serial.println(topic);
  handle_command(payload, length);
}

void connect_wifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(DEVICE_ID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
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
  });

  ArduinoOTA.onError([](ota_error_t error) {
    Serial.print("OTA error ");
    Serial.println(static_cast<int>(error));
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
      bool subscribed = mqtt_client.subscribe(topic_for("cmd").c_str());
      Serial.print(subscribed ? "Subscribed to " : "Failed to subscribe to ");
      Serial.println(topic_for("cmd"));
      publish_hello();
      publish_state();
    } else {
      Serial.print("failed rc=");
      Serial.print(mqtt_client.state());
      Serial.println(", retrying");
      delay(MQTT_RECONNECT_DELAY_MS);
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(1000);
  Serial.println();
  Serial.println("Alice ESP32 relay node starting");

  pinMode(OUTPUT_PIN, OUTPUT);
  apply_output(false);

  mqtt_client.setServer(MQTT_HOST, MQTT_PORT);
  mqtt_client.setCallback(mqtt_callback);
  mqtt_client.setBufferSize(1024);
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
  if (mqtt_client.connected() && (last_state_publish_ms == 0 || millis() - last_state_publish_ms >= STATE_PUBLISH_INTERVAL_MS)) {
    publish_state();
  }
  delay(10);
}
