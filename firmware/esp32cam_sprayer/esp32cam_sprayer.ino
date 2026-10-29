/*
  esp32cam_sprayer.ino
  ---------------------------------------------------------------------------
  BCE497J - Deep Learning and IoT-Based Real-Time Variable-Rate Chemical
  Spraying System for Disease Control in Paddy Crop.

  AI-Thinker ESP32-CAM controller. One cycle:
    1. Wait for a trigger (push button on GPIO13 to GND, or Blynk button).
    2. Capture one RGB565 QVGA (320x240) frame.
    3. POST the RAW RGB565 bytes to the Flask /predict API with
       ?fmt=rgb565&w=<w>&h=<h>. This board's clone OV2640 has NO hardware
       JPEG (PIXFORMAT_JPEG -> error 0x106), so the server converts the frame
       instead of the ESP32 (app/server.py, _pil_from_rgb565).
    4. Parse the JSON reply and light the matching status LED.
    5. Send "S<ms>,<cat>*<HH>\n" (XOR checksum) to the Arduino Nano to open
       the valve.
    6. (Optional) push severity/category/usage to Blynk.

  HARD RULE: never use GPIO16 or GPIO17. GPIO16 is the PSRAM chip-select on
  the AI-Thinker ESP32-CAM (CONFIG_D0WD_PSRAM_CS_IO=16). Reconfiguring it
  disables PSRAM, and malloc() > 4 KB is served from PSRAM, so the camera
  driver, HTTP stack and any large buffer then crash (LoadProhibited).

  Tested toolchain: arduino-esp32 core 2.0.17, ArduinoJson 7.4.3,
  Blynk 1.4.0 (only if BLYNK_ENABLED 1). Blynk is OFF by default.
*/

// --------------------------------------------------------------------- //
// BLYNK CONFIG - must be defined before any include. Set BLYNK_ENABLED to 1
// to re-enable the dashboard once the core loop is confirmed working.
// --------------------------------------------------------------------- //
// Credentials (Wi-Fi, server URL, Blynk) live in secrets.h; copy secrets.h.example
// to secrets.h and fill it in. secrets.h is git-ignored.
#include "secrets.h"

#define BLYNK_ENABLED    0
#if BLYNK_ENABLED
  #define BLYNK_PRINT Serial
#endif

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#if BLYNK_ENABLED
  #include <BlynkSimpleEsp32.h>
#endif

// WIFI_SSID, WIFI_PASSWORD and PREDICT_URL come from secrets.h (see above).

// --------------------------------------------------------------------- //
// Pin map (AI-Thinker ESP32-CAM). Do not change the camera pins.
// --------------------------------------------------------------------- //
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// !!! NEVER use GPIO16 or GPIO17 on this board. In the core's sdkconfig
// CONFIG_D0WD_PSRAM_CS_IO=16 / CLK_IO=17: GPIO16 is the PSRAM chip-select.
// Calling pinMode() on it disables PSRAM, and because malloc() > 4 KB is
// served from PSRAM, that caused every LoadProhibited crash / malloc failure
// seen during bring-up (camera init, JPEG encode, HTTP POST).
// Free pins on this board with camera + PSRAM + no SD card: 2, 12, 13, 14, 15
// (GPIO4 drives the onboard flash LED; GPIO0 is the camera XCLK).
#define TRIGGER_BUTTON_PIN 13  // push button to GND (INPUT_PULLUP). Was 16.
#define LED_HEALTHY_PIN    12  // category 0 (strapping pin: LED+resistor to GND is fine)
#define LED_LOW_PIN         2  // category 1 (was 13, now used by the button)
#define LED_MEDIUM_PIN     14  // category 2
#define LED_HIGH_PIN       15  // category 3

#define TRIGGER_PERIOD_MS   0        // 0 = button/Blynk only, no auto timer
#define SERIAL_BAUD_TO_NANO 9600
#define HTTP_TIMEOUT_MS     15000

#if BLYNK_ENABLED
#define VPIN_SEVERITY      V0
#define VPIN_CATEGORY      V1
#define VPIN_CHEMICAL_LOG  V2
#define VPIN_ALERT         V3
#define VPIN_REMOTE_TRIGGER V4
bool remoteTriggerRequested = false;
BLYNK_WRITE(VPIN_REMOTE_TRIGGER) {
  if (param.asInt() == 1) {
    remoteTriggerRequested = true;
  }
}
#endif

unsigned long lastAutoTrigger = 0;

// --------------------------------------------------------------------- //
// Camera init. This board's clone OV2640 has no hardware JPEG
// (PIXFORMAT_JPEG -> error 0x106), so frames are captured as RGB565 and sent
// raw; the Flask server converts them. Every config field is defined (the
// struct is value-initialised) and the frame buffer lives in PSRAM, which is
// healthy now that GPIO16 (PSRAM chip-select) is no longer touched.
// --------------------------------------------------------------------- //
bool initCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_RGB565;   // clone sensor: no HW JPEG
  config.frame_size   = FRAMESIZE_QVGA;     // 320x240 (153,600 bytes RGB565)
  config.jpeg_quality = 12;                 // unused for RGB565
  config.fb_count     = 1;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[cam] init failed, error 0x%x\n", err);
    return false;
  }
  return true;
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[wifi] connecting");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[wifi] connected, IP ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("[wifi] could not connect within 20 s, will retry on next trigger");
  }
}

void setStatusLed(int categoryCode) {
  digitalWrite(LED_HEALTHY_PIN, categoryCode == 0 ? HIGH : LOW);
  digitalWrite(LED_LOW_PIN,     categoryCode == 1 ? HIGH : LOW);
  digitalWrite(LED_MEDIUM_PIN,  categoryCode == 2 ? HIGH : LOW);
  digitalWrite(LED_HIGH_PIN,    categoryCode == 3 ? HIGH : LOW);
}

// Send "S<ms>,<cat>*<HH>\n" to the Nano, where <HH> is the 2-digit hex XOR of
// every character from 'S' up to (not including) '*'.
//
// This UART (GPIO1/TX0) is also the ESP32's debug console, so the Nano sees
// all the [wifi]/[cycle]/boot-ROM text too. The checksum lets the Nano accept
// ONLY a genuine command and ignore everything else, so noise can never open
// the valve. Must match valve_controller.ino (v2).
void sendSprayCommandToNano(float sprayTimeS, int categoryCode) {
  long ms = (long)(sprayTimeS * 1000.0 + 0.5);
  if (ms < 0) {
    ms = 0;
  }
  if (categoryCode < 0 || categoryCode > 3) {
    categoryCode = 0;
  }

  char body[24];
  snprintf(body, sizeof(body), "S%ld,%d", ms, categoryCode);

  uint8_t x = 0;
  for (const char *p = body; *p; p++) {
    x ^= (uint8_t)(*p);
  }

  char line[32];
  snprintf(line, sizeof(line), "%s*%02X\n", body, x);

  // A leading newline terminates any partial debug text already on the wire,
  // so the command always starts on a fresh line at the Nano.
  Serial.print('\n');
  Serial.print(line);
  Serial.flush();
}

// Capture an RGB565 frame and POST the RAW bytes to Flask. We do NOT encode
// JPEG on the ESP32: this clone sensor has no hardware JPEG, and the software
// encoder (frame2jpg) exhausts the ESP32's scarce internal RAM and crashes
// (JPG buffer malloc failed / LoadProhibited). Instead the server accepts the
// raw RGB565 frame (fmt=rgb565 with width/height) and does the conversion on
// the PC, which has ample memory. The raw frame already lives in the camera
// frame buffer, so no extra allocation is needed here.
bool captureAndPredict(JsonDocument &outJson) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[cam] capture failed");
    return false;
  }

  Serial.printf("[cam] captured RGB565 %ux%u, %u bytes\n",
                fb->width, fb->height, (unsigned)fb->len);

  // Show the real WiFi state and signal, so a -1 POST failure can be told
  // apart from a dropped link.
  Serial.printf("[wifi] status=%d RSSI=%d IP=%s\n",
                (int)WiFi.status(), (int)WiFi.RSSI(),
                WiFi.localIP().toString().c_str());

  // Make sure WiFi is actually up right before the POST; reconnect if not.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] not connected before POST, reconnecting");
    connectWiFi();
  }

  bool ok = false;
  if (WiFi.status() == WL_CONNECTED) {
    // Tell the server this is a raw RGB565 frame and its dimensions, and ask
    // it to omit the large overlay_png field (overlay=0): the ESP32 only needs
    // the small decision fields, and the base64 PNG overflowed the JSON
    // buffer (JSON parse error: NoMemory).
    String url = String(PREDICT_URL) + "?fmt=rgb565&overlay=0&w=" +
                 String(fb->width) + "&h=" + String(fb->height);

    // Try the POST up to 3 times; a single -1 (failed connection) is often a
    // transient, so we retry instead of giving up the whole cycle.
    int code = -1;
    for (int attempt = 1; attempt <= 3 && code != 200; attempt++) {
      HTTPClient http;
      http.setConnectTimeout(5000);
      http.setTimeout(HTTP_TIMEOUT_MS);
      if (!http.begin(url)) {
        Serial.printf("[api] attempt %d: http.begin failed\n", attempt);
        delay(300);
        continue;
      }
      http.addHeader("Content-Type", "application/octet-stream");
      code = http.POST(fb->buf, fb->len);
      Serial.printf("[api] attempt %d: HTTP code %d\n", attempt, code);
      if (code == 200) {
        String body = http.getString();
        DeserializationError derr = deserializeJson(outJson, body);
        if (!derr) {
          ok = true;
        } else {
          Serial.print("[api] JSON parse error: ");
          Serial.println(derr.c_str());
        }
      }
      http.end();
      if (code != 200) {
        delay(400);
      }
    }
    if (!ok && code != 200) {
      Serial.print("[api] POST failed after retries, last HTTP code ");
      Serial.println(code);
    }
  } else {
    Serial.println("[api] WiFi not connected, skipping this cycle");
  }

  esp_camera_fb_return(fb);  // release the frame buffer
  return ok;
}

#if BLYNK_ENABLED
void publishToBlynk(JsonDocument &j) {
  float severity = j["severity_percent"] | 0.0;
  const char *category = j["category"] | "Healthy";
  float volumeMl = j["spray_params"]["a_ml_per_hill"] | 0.0;
  Blynk.virtualWrite(VPIN_SEVERITY, severity);
  Blynk.virtualWrite(VPIN_CATEGORY, category);
  Blynk.virtualWrite(VPIN_CHEMICAL_LOG, volumeMl);
  if (severity > 20.0) {
    Blynk.virtualWrite(VPIN_ALERT, "High severity detected, full dose sprayed");
  }
}
#endif

bool triggerRequested() {
  static bool lastButtonState = HIGH;
  bool requested = false;

  bool buttonState = digitalRead(TRIGGER_BUTTON_PIN);
  if (lastButtonState == HIGH && buttonState == LOW) {
    requested = true;  // falling edge, active LOW pull-up
  }
  lastButtonState = buttonState;

  if (TRIGGER_PERIOD_MS > 0 && millis() - lastAutoTrigger >= (unsigned long)TRIGGER_PERIOD_MS) {
    lastAutoTrigger = millis();
    requested = true;
  }

#if BLYNK_ENABLED
  if (remoteTriggerRequested) {
    remoteTriggerRequested = false;
    requested = true;
  }
#endif

  return requested;
}

void runOneCycle() {
  Serial.println("[cycle] triggered");
  // 4 KB is plenty for the decision fields now that overlay_png is omitted
  // (see captureAndPredict: the request sends overlay=0). Dynamic so it lives
  // on the heap, not the stack.
  DynamicJsonDocument doc(4096);
  if (!captureAndPredict(doc)) {
    Serial.println("[cycle] no result this time, LEDs unchanged, no code sent to Nano");
    return;
  }

  const char *diseaseClass = doc["disease_class"] | "Unknown";
  float confidence = doc["confidence"] | 0.0;
  float severity = doc["severity_percent"] | 0.0;
  int categoryCode = doc["category_code"] | 0;
  float sprayTime = doc["spray_time_s"] | 0.0;

  Serial.printf("[cycle] class=%s conf=%.2f severity=%.2f%% category_code=%d ts=%.2fs\n",
                diseaseClass, confidence, severity, categoryCode, sprayTime);

  setStatusLed(categoryCode);
  sendSprayCommandToNano(sprayTime, categoryCode);

#if BLYNK_ENABLED
  publishToBlynk(doc);
#endif
}

void setup() {
  Serial.begin(SERIAL_BAUD_TO_NANO);
  delay(200);
  Serial.println();
  Serial.println("[boot] PaddyGuard ESP32-CAM sprayer controller");

  // Trigger button on GPIO13 (NOT 16: GPIO16 is the PSRAM chip-select).
  pinMode(TRIGGER_BUTTON_PIN, INPUT_PULLUP);

  Serial.printf("[trace] psramFound=%d freeHeap=%u psramSize=%u\n",
                (int)psramFound(), (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getPsramSize());
  Serial.println("[trace] about to call initCamera()");
  Serial.flush();

  if (!initCamera()) {
    Serial.println("[boot] camera init failed, halting (check ribbon cable seating)");
    while (true) {
      delay(1000);
    }
  }
  Serial.println("[trace] initCamera() returned OK");
  Serial.flush();

  // Status LEDs (GPIO12/2/14/15 are SD-card lines, unused here).
  pinMode(LED_HEALTHY_PIN, OUTPUT);
  pinMode(LED_LOW_PIN, OUTPUT);
  pinMode(LED_MEDIUM_PIN, OUTPUT);
  pinMode(LED_HIGH_PIN, OUTPUT);
  setStatusLed(-1);  // all off until first result

  connectWiFi();

#if BLYNK_ENABLED
  // Only start Blynk if WiFi actually came up. Calling Blynk.connect() without
  // a working network connection crashed (LoadProhibited) in Blynk 1.4.0 on
  // the ESP32 3.x core. With WiFi confirmed up first, the connect path is
  // safe; if WiFi is down, we skip Blynk entirely and the spray loop still
  // runs. loop() retries Blynk once WiFi reconnects.
  if (WiFi.status() == WL_CONNECTED) {
    Blynk.config(BLYNK_AUTH_TOKEN);
    Blynk.connect(5000);
  } else {
    Serial.println("[blynk] WiFi down, skipping Blynk connect for now");
  }
#endif

  Serial.println("[boot] ready, waiting for trigger");
}

void loop() {
#if BLYNK_ENABLED
  // Only service Blynk when it is actually connected; running it while
  // disconnected can fault on the 3.x core.
  if (Blynk.connected()) {
    Blynk.run();
  }
#endif

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (triggerRequested()) {
    runOneCycle();
  }

  delay(20);
}
