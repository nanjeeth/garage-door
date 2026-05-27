/*
  Garage Door Controller — ESP32 Firmware

  Wiring:
    - Relay signal → GPIO 26 (triggers garage door opener)
    - Reed switch  → GPIO 27 (detects door open/closed)
    - Reed switch other leg → GND

  API:
    GET  /status   → {"door": "open"|"closed"}
    POST /trigger  → pulses relay for 500ms (like pressing the wall button)
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ——— CONFIGURE THESE ———
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* AUTH_TOKEN     = "change-me-to-a-secret";  // must match server .env
const char* SERVER_URL     = "http://YOUR_SERVER_IP:8002/api/door/webhook";
// ————————————————————————

#define RELAY_PIN   26
#define REED_PIN    27
#define STATUS_LED  2   // built-in LED

WebServer server(80);

bool doorOpen = false;
bool lastDoorState = false;
unsigned long lastDebounce = 0;
const unsigned long DEBOUNCE_MS = 500;


bool checkAuth() {
  if (!server.hasHeader("Authorization")) {
    server.send(401, "application/json", "{\"error\":\"unauthorized\"}");
    return false;
  }
  String auth = server.header("Authorization");
  String expected = "Bearer " + String(AUTH_TOKEN);
  if (auth != expected) {
    server.send(403, "application/json", "{\"error\":\"forbidden\"}");
    return false;
  }
  return true;
}


void handleStatus() {
  if (!checkAuth()) return;

  String status = doorOpen ? "open" : "closed";
  String json = "{\"door\":\"" + status + "\"}";
  server.send(200, "application/json", json);
}


void handleTrigger() {
  if (!checkAuth()) return;

  Serial.println("Triggering relay...");
  digitalWrite(RELAY_PIN, HIGH);
  delay(500);
  digitalWrite(RELAY_PIN, LOW);

  server.send(200, "application/json", "{\"triggered\":true}");
}


void notifyServer(bool isOpen) {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  String body = isOpen ? "{\"door\":\"open\"}" : "{\"door\":\"closed\"}";
  int code = http.POST(body);

  if (code > 0) {
    Serial.printf("Webhook sent, response: %d\n", code);
  } else {
    Serial.printf("Webhook failed: %s\n", http.errorToString(code).c_str());
  }
  http.end();
}


void checkDoorSensor() {
  bool currentState = digitalRead(REED_PIN) == HIGH;  // HIGH = open (magnet away)

  if (currentState != lastDoorState && millis() - lastDebounce > DEBOUNCE_MS) {
    lastDebounce = millis();
    lastDoorState = currentState;
    doorOpen = currentState;

    Serial.printf("Door state changed: %s\n", doorOpen ? "OPEN" : "CLOSED");
    digitalWrite(STATUS_LED, doorOpen ? HIGH : LOW);

    notifyServer(doorOpen);
  }
}


void setup() {
  Serial.begin(115200);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(REED_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED, OUTPUT);

  digitalWrite(RELAY_PIN, LOW);

  // Connect WiFi
  Serial.printf("Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());

  // Read initial door state
  doorOpen = digitalRead(REED_PIN) == HIGH;
  lastDoorState = doorOpen;
  digitalWrite(STATUS_LED, doorOpen ? HIGH : LOW);
  Serial.printf("Initial door state: %s\n", doorOpen ? "OPEN" : "CLOSED");

  // Setup HTTP server
  server.collectHeaders("Authorization");
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/trigger", HTTP_POST, handleTrigger);
  server.begin();

  Serial.println("HTTP server started on port 80");
}


void loop() {
  server.handleClient();
  checkDoorSensor();
  delay(50);
}
