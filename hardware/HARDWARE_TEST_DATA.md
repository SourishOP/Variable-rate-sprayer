# Hardware test data sheet

Fill this with the REAL readings from your built prototype. The report quotes
these values exactly as written here. If a test was not done, write NOT DONE and
the report will treat that item as future work instead of a result.

Units: volume in mL, time in seconds, voltage in V.

## A. Prototype details

| Item | Your value |
|---|---|
| Date the prototype was completed | NOT DONE (ESP32-CAM and Nano flashed and bench tested; full prototype with liquid path not yet assembled) |
| Place of build and testing | |
| Power source used (3 x 18650 pack or 12 V lead-acid) | NOT DONE (both boards tested on USB power only so far) |
| Battery voltage when fully charged (V) | |
| Solenoid valve actually used (make and model) | 12 V DC solenoid valve, coil type (label reads "DC12V"; exact make/model not recorded). Coil terminals have no polarity; wired to relay NO and ground. Water flow direction follows the arrow moulded on the valve body. |
| Pump actually used (make and model) | |
| Spray nozzle actually used | |
| Any part that differs from hardware_implementation_plan.md | 1. Trigger button moved from GPIO0 to GPIO16 (early draft) to GPIO13 (final), see section I below. 2. Camera module has no hardware JPEG; firmware captures RGB565 and the server decodes it, see section I. 3. Pump wired directly to +12V with no manual on/off switch (deliberate simplification, the solenoid valve gates the spray, not the pump). 4. BLYNK_ENABLED is 0 in the flashed firmware; the dashboard is not currently live from the physical prototype. |

## B. Bench tests (each module alone)

| Module | What was checked | Result (Pass or Fail) | Measured value or note |
|---|---|---|---|
| ESP32-CAM | Camera init, WiFi connect and one API call (own test sketch, not the CameraWebServer example) | Pass | See section C log; freeHeap 284264, psramSize 4192123 at boot |
| Arduino Nano | Serial Monitor boot message and bench digit test mode | Pass | "[boot] PaddyGuard valve controller ready" |
| Relay module | Click heard, COM to NO closes when D7 is HIGH (Nano bench test, categories 1 to 3) | Pass | See section E, bench test log |
| LM2596 buck converter | Output set to 5 V and checked with a multimeter | NOT DONE | Unloaded (V): ; under load (V): |
| Pump | Primes and pumps water from a bucket | NOT DONE | |
| Solenoid valve | Closed with no power, opens with 12 V (dry, no water, relay bench test) | Pass | Relay audibly clicked and valve visibly opened and closed for the commanded duration on categories 1, 2 and 3; no actuation on category 0 |

## C. Integration tests

| Test | Result (Pass or Fail) | Note |
|---|---|---|
| ESP32-CAM to Nano serial link sends and receives codes 0 to 3 | Pass (one cycle) | Nano received "S2900,3" and the relay/valve log matches, see the two logs in section E and below |
| Nano to relay to solenoid dry run with test durations | Pass | See section E bench test log |
| ESP32-CAM sends the frame to the Flask API and reads the JSON reply | Pass | Frame sent as raw RGB565 (fmt=rgb565, see section I), not JPEG; server replied and ESP32 parsed it without the earlier NoMemory error |
| ESP32-CAM updates the Blynk dashboard | NOT DONE | BLYNK_ENABLED is 0 in the flashed firmware (see section A) |
| Full cycle on USB power | Pass (one automated cycle, see note below) | ESP32-CAM Serial Monitor log: see below. Caveat: the [cycle] triggered line has the same timestamp as "ready, waiting for trigger", so this cycle almost certainly fired on a GPIO13 boot float rather than a deliberately timed button press. The capture, classification and serial command sent to the Nano are still genuine. |
| Full cycle on the 12 V battery and buck converter | NOT DONE | Tested on USB power only so far |

Real ESP32-CAM Serial Monitor log for the one recorded integration cycle:

```
[boot] PaddyGuard ESP32-CAM sprayer controller
[trace] psramFound=1 freeHeap=284264 psramSize=4192123
[trace] about to call initCamera()
[trace] initCamera() returned OK
cam_hal: EV-EOF-OVF
[wifi] connecting..
[wifi] connected, IP 172.20.10.2
[boot] ready, waiting for trigger
[cycle] triggered
[cam] captured RGB565 320x240, 153600 bytes
[cycle] class=Bacterial_Blight conf=0.48 severity=26.78% category_code=3 ts=2.90s
S2900,3
```

## D. Flow calibration (Qs)

NOT DONE. The pump and tubing have not been assembled with the solenoid
valve yet, so no timed water collection has been run. The design value
below is a placeholder used for the firmware's optional debug printout and
for the worked examples in the report; it is not a measured result.

| Item | Value |
|---|---|
| Battery voltage during the test (V) | NOT DONE |
| Trial 1: volume collected in 10 s (mL) | NOT DONE |
| Trial 2: volume collected in 10 s (mL) | NOT DONE |
| Trial 3: volume collected in 10 s (mL) | NOT DONE |
| Qs used in the firmware (mL/s) | 3.5 (design value, QS_MLS_DESIGN in valve_controller.ino, NOT yet measured) |
| A used in the firmware (L/ha) | 500 (design value, APP_RATE_LPH) |
| d used in the firmware (hills per m2) | 25 (design value, HILL_DENSITY_M2) |
| Maximum valve open time cap in the firmware (s) | 5.0 (MAX_VALVE_OPEN_MS = 5000, confirmed in valve_controller.ino) |

## E. Spray volume check (water, per category)

NOT DONE with water. A dry bench test (relay and valve timing only, no
water in the tank, no measuring cup) was run using the Nano's single digit
test mode and is reported below for the timing behaviour only; the "mL"
column here is the firmware's own printed figure at the unmeasured design
flow rate (QS_MLS_DESIGN = 3.5 mL/s, see section D) and is NOT a measured
dispensed volume. Replace this whole table with a real measured volume
once the flow calibration in section D and a wet spray test are done.

Real Nano Serial Monitor log, dry bench test, all four categories:

```
[boot] PaddyGuard valve controller ready
[boot] bench test: type 0, 1, 2 or 3 in this Serial Monitor to dry-run the relay
[bench] test category 0
[valve] category Healthy (or ts=0), no spray this cycle
[bench] test category 1
[valve] opening for 1250 ms, category code 1, expected volume at design Qs: 4.38 mL
[valve] closed
[bench] test category 2
[valve] opening for 1875 ms, category code 2, expected volume at design Qs: 6.56 mL
[valve] closed
[bench] test category 3
[valve] opening for 2500 ms, category code 3, expected volume at design Qs: 8.75 mL
[valve] closed
```

| Category | ts set by firmware (ms) | Expected volume at design Qs (mL, NOT measured) | Actual measured volume (mL) |
|---|---|---|---|
| Healthy (0) | 0 | 0 | NOT DONE |
| Low (1) | 1250 | 4.38 | NOT DONE |
| Medium (2) | 1875 | 6.56 | NOT DONE |
| High (3) | 2500 | 8.75 | NOT DONE |

## F. End to end cycle time (at least 10 runs)

| Run | Capture to API reply (s) | Reply to valve opening (s) | Total (s) | Class returned | Category | Network used |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

## G. Class wise functional test (at least 3 images per class, shown on a screen or printed)

| Image used | Expected class | Class returned | Severity % shown | LED that lit | Volume sprayed (mL) | Pass or Fail |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

## H. Field trial (write NOT DONE if you did not run one)

| Item | Value |
|---|---|
| Date and place | |
| Crop stage and weather | |
| Length of row and number of hills | |
| Liquid used with constant rate spraying (mL) | |
| Liquid used with variable rate spraying (mL) | |
| Number of spray cycles logged | |
| Notes (sunlight, shade hood, problems) | |

## I. Real problems you faced and how you fixed them (3 to 6 items)

| Problem | Cause | Fix |
|---|---|---|
| Camera init crashed (Guru Meditation Error, LoadProhibited) once the trigger button was wired to GPIO16 | GPIO16 is the ESP32's PSRAM chip select pin (confirmed from the Arduino core's sdkconfig, CONFIG_D0WD_PSRAM_CS_IO=16); setting it as a button input disabled PSRAM, and the camera driver's frame buffer allocation then failed | Moved the trigger button to GPIO13, and moved the status LED that used to be on GPIO13 (category 1, Low) to GPIO2 instead. Never use GPIO16 or GPIO17 for anything else on this board. |
| Camera would not capture JPEG (error: "JPEG format is not supported on this sensor") | The physical camera module on this board, although sold as an OV2640 AI-Thinker ESP32-CAM, does not support hardware JPEG encoding; confirmed with a test sketch that the same module captures fine in grayscale and RGB565 | Capture 320x240 RGB565 instead of JPEG on the ESP32, send the raw bytes over HTTP with fmt=rgb565, and decode them into a normal image on the Flask server (_pil_from_rgb565 in app/server.py). The model and severity logic are unchanged. |
| ESP32's JSON parser ran out of memory reading the server's reply ("NoMemory") | The server's normal response includes a large base64 encoded mask image (overlay_png) meant for the web demo, too big for the ESP32's JSON buffer | Server skips overlay_png for ESP32 requests (new query parameter overlay=0); ESP32's own JSON buffer increased from 1024 to 4096 bytes |
| ESP32 could not connect to the WiFi hotspot | The iPhone hotspot's name contains a typographic ("curly") apostrophe, not the plain keyboard apostrophe, and WiFi.begin() needs an exact character match | Wrote the WiFi network name in the firmware using the matching Unicode escape for the curly apostrophe |
| ESP32 connected to WiFi only intermittently or not at all | The ESP32 cannot join a 5 GHz WiFi network | Enabled "Maximize Compatibility" in the phone's Personal Hotspot settings, which forces the hotspot to 2.4 GHz |

## J. Files you added

| Folder | What you put there |
|---|---|
| photos\ | NOT DONE, still empty |
| screenshots\ | NOT DONE, still empty |
| firmware\ | esp32cam_sprayer.ino, valve_controller.ino (both flashed and tested on real hardware), BLYNK_SETUP.md, push_to_blynk.py, plus three throwaway diagnostic sketches used only during bring up (cam_probe, cam_capture_test) which are not part of the delivered firmware |
