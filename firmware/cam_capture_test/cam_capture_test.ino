/*
  cam_capture_test.ino  -- throwaway diagnostic, NOT part of the project.
  Tries to actually CAPTURE a frame (not just read the sensor ID) in three
  formats and reports the real byte length for each. If any capture returns
  a non-zero length, the camera can produce an image.

  Flash this, open Serial Monitor at 115200, press RST, read the results.
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

void fillPins(camera_config_t &c) {
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer   = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;
  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;
  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;  c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;  c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
}

void tryCapture(const char *name, pixformat_t fmt, framesize_t fs) {
  camera_config_t config;
  fillPins(config);
  config.pixel_format = fmt;
  config.frame_size   = fs;
  config.fb_count     = 1;
  config.jpeg_quality = 12;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[cap] %-9s init FAILED error 0x%x\n", name, err);
    return;
  }

  // Grab a couple of frames; first frame after init is often blank.
  camera_fb_t *fb = NULL;
  for (int i = 0; i < 3; i++) {
    if (fb) esp_camera_fb_return(fb);
    fb = esp_camera_fb_get();
    delay(100);
  }

  if (!fb) {
    Serial.printf("[cap] %-9s capture returned NULL (no frame)\n", name);
  } else {
    Serial.printf("[cap] %-9s CAPTURED %u bytes (%ux%u)\n",
                  name, (unsigned)fb->len, fb->width, fb->height);
    esp_camera_fb_return(fb);
  }

  esp_camera_deinit();
  delay(300);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("[cap] camera CAPTURE test (tries to grab a real frame)");

  tryCapture("GRAYSCALE", PIXFORMAT_GRAYSCALE, FRAMESIZE_QVGA);
  tryCapture("RGB565",    PIXFORMAT_RGB565,    FRAMESIZE_QVGA);
  tryCapture("JPEG",      PIXFORMAT_JPEG,      FRAMESIZE_VGA);

  Serial.println("[cap] done. Any line with 'CAPTURED ... bytes' = camera works in that format.");
}

void loop() { delay(1000); }
