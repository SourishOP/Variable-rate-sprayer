/*
  cam_probe.ino  -- throwaway diagnostic, NOT part of the project.
  Identifies which camera sensor is on this AI-Thinker ESP32-CAM board.
  Initializes in GRAYSCALE (always supported) so init won't fail, then
  prints the sensor's PID so we know whether JPEG is available.

  Flash this, open Serial Monitor at 115200 (NOT 9600 for this probe),
  press RST, and read the "[probe] sensor PID = 0x..." line.
*/

#include "esp_camera.h"

#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("[probe] camera sensor identification");

  camera_config_t config;
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
  config.xclk_freq_hz = 10000000;  // lowered from 20MHz to help a marginal clone SCCB bus

  // Grayscale is supported by every sensor, so init succeeds and we can
  // read the sensor id regardless of JPEG support.
  config.pixel_format = PIXFORMAT_GRAYSCALE;
  config.frame_size   = FRAMESIZE_QVGA;
  config.fb_count     = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[probe] init FAILED even in grayscale, error 0x%x\n", err);
    Serial.println("[probe] that points to wiring/ribbon, not sensor format");
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  if (!s) {
    Serial.println("[probe] got null sensor handle");
    return;
  }

  Serial.printf("[probe] sensor PID = 0x%02x  (VER=0x%02x MIDH=0x%02x MIDL=0x%02x)\n",
                s->id.PID, s->id.VER, s->id.MIDH, s->id.MIDL);

  switch (s->id.PID) {
    case 0x26: Serial.println("[probe] => OV2640  (JPEG SHOULD work)"); break;
    case 0x36: Serial.println("[probe] => OV3660  (JPEG supported on 3.x driver)"); break;
    case 0x55: Serial.println("[probe] => OV5640  (JPEG supported)"); break;
    case 0x30: Serial.println("[probe] => OV7670 / OV7725 family (NO hardware JPEG)"); break;
    default:   Serial.println("[probe] => unknown/clone sensor"); break;
  }
}

void loop() {
  delay(1000);
}
