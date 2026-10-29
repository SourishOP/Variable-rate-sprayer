# firmware: ESP32-CAM and Arduino Nano

| Path | Board | Purpose |
|------|-------|---------|
| `esp32cam_sprayer/esp32cam_sprayer.ino` | AI-Thinker ESP32-CAM | Capture on trigger, POST the RGB565 frame to `/predict`, light a status LED, send `S<ms>,<cat>*<HH>` to the Nano |
| `esp32cam_sprayer/secrets.h.example` | | Template for Wi-Fi, server URL and Blynk values |
| `valve_controller/valve_controller.ino` | Arduino Nano | Receives the spray command and opens the relay-driven solenoid valve for the requested time |
| `cam_probe/cam_probe.ino` | ESP32-CAM | Diagnostic: reads the camera sensor ID |
| `cam_capture_test/cam_capture_test.ino` | ESP32-CAM | Diagnostic: tries to capture a frame in several formats |
| `push_to_blynk.py` | PC | Replays the recorded pipeline results to the Blynk dashboard |
| `BLYNK_SETUP.md` | | Blynk template and datastream setup |

## Set up credentials

```text
firmware/esp32cam_sprayer/secrets.h.example  ->  copy to secrets.h and fill in
```

`secrets.h` is git-ignored. Set `WIFI_SSID`, `WIFI_PASSWORD` and `PREDICT_URL`
(the LAN address of the machine running `app/server.py`, not `localhost`).
Blynk values are only needed if you set `BLYNK_ENABLED` to 1 in the sketch; it is
0 by default.

## Flash

- Toolchain used: arduino-esp32 core 2.0.17, ArduinoJson 7.4.3, Blynk 1.4.0
  (only if Blynk is enabled).
- ESP32-CAM: board "AI Thinker ESP32-CAM". Trigger button on GPIO13 to GND.
  Do not use GPIO16 or GPIO17 (PSRAM).
- Nano: SoftwareSerial RX on D10 (from ESP32-CAM GPIO1/TX), relay on D7, 9600
  baud. Bench mode over the USB serial monitor: send `0` to `3` for test sprays and
  `x` to force the valve closed.
- The camera on the tested board has no hardware JPEG, so the sketch sends raw
  RGB565 and `app/server.py` converts it.

## Blynk replay

```powershell
$env:BLYNK_AUTH_TOKEN = "your-device-auth-token"
python firmware/push_to_blynk.py
```

Wiring and the full build are in [../hardware](../hardware/README.md).
Back to the [main README](../README.md).