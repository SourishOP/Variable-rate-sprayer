# HARDWARE IMPLEMENTATION

## 5.1 OVERVIEW

This chapter describes the physical build that carries out the spray
decision in the field: the parts list, the wiring, the power system, the
liquid path, the firmware behaviour, and the assembly and calibration
procedure. The design in this chapter follows `hardware_implementation_plan.md`,
the team's own hardware design document, because it is the most complete and
most detailed source of hardware design information available for this
report, except where the team's own bring up work on the real prototype
found a problem with the plan and changed it, in which case that change is
stated and the reason is given. Any value in this chapter that the team has
since measured on the real, built prototype is taken from
`Capstone/hardware_evidence/HARDWARE_TEST_DATA.md` and is clearly marked as
measured. At the time of writing this report, the ESP32-CAM and the Arduino
Nano have both been flashed and bench tested, and the two boards have been
wired together and run through one integration cycle (section 5.8.2), but
the flow rate calibration, the spray volume check with water, the full
field trial and the full ten run cycle timing table are not yet done
(section 5.8.1, section 5.8.2); every value that would normally come from
one of those remaining tests is stated plainly as not yet available,
rather than invented.

## 5.2 BILL OF MATERIALS

{{TABLE:bom|Bill of materials for the hardware prototype.}}
| # | Component | Specification | Approx. cost (Rs.) |
|---|---|---|---|
| 1 | ESP32-CAM | AI-Thinker, OV2640 sensor, WiFi and Bluetooth, 4 MB PSRAM, microSD slot | 450 to 550 |
| 2 | ESP32-CAM programmer | ESP32-CAM-MB, USB micro-B, CH340 chip | 150 to 200 |
| 3 | Arduino Nano | V3.0, ATmega328P, CH340, mini USB | 200 to 280 |
| 4 | Solenoid valve | 12 V DC, normally closed, 1/2 inch, plastic body | 250 to 400 |
| 5 | Relay module | 5 V, 1 channel, optocoupler isolated (Songle SRD-05VDC-SL-C) | 45 to 70 |
| 6 | Water pump | R385 type, 12 V DC diaphragm, 1.5 to 2 L/min, self priming | 200 to 350 |
| 7 | Power pack | 3 x 18650 Li-ion cells (3.7 V, 2,600 mAh) with holder, or a 12 V, 2 A sealed lead acid battery | 300 to 450 |
| 8 | Buck converter | LM2596, adjustable, 12 V to 5 V, with trim pot | 45 to 70 |
| 9 | Spray nozzle | Adjustable brass, hollow cone pattern, 1/4 inch thread | 80 to 150 |
| 10 | Silicone tubing | 6 mm internal, 8 mm external diameter, food grade, about 2 m | 60 to 100 |
| 11 | Jumper wires and breadboard | Male to female and male to male kits, mini breadboard | 100 to 150 |
| 12 | Push button | 12 mm momentary push button | 10 to 20 |
| 13 | Inline fuse | 2 A blade fuse with inline holder | about 30 |

Total target cost: approximately Rs. 2,250 to Rs. 2,400, with a full possible
range of Rs. 1,930 to Rs. 2,720 depending on exact parts sourced. At the
time of writing this report, no parts had yet been purchased (section
5.11), so this is a planning estimate only; the actual amount spent should
replace this estimate once procurement is complete.

## 5.3 CIRCUIT AND WIRING

Figure 5.1 shows the full circuit and wiring diagram. Table 5.1 lists the
ESP32-CAM pin usage and Table 5.2 lists the Arduino Nano pin usage.

{{FIG:circuit_wiring|figures/fig_circuit_wiring.png|Complete circuit and wiring diagram of the prototype.}}

{{TABLE:esp32_pins|ESP32-CAM pin usage, as implemented and flashed in esp32cam_sprayer.ino (Appendix 4).}}
| ESP32-CAM pin | Connects to | Notes |
|---|---|---|
| 5V | LM2596 5 V output | Power in, about 300 mA while active |
| GND | Common ground bus | Shared with Nano, relay and buck converter |
| GPIO1 (U0TXD) | Arduino Nano D10 (SoftwareSerial RX) | Sends the spray command, disconnect while flashing |
| GPIO13 | Push button to GND | Manual trigger |
| GPIO12 | Status LED, category 0 (Healthy) | Through a 220 ohm resistor to GND |
| GPIO2 | Status LED, category 1 (Low) | Through a 220 ohm resistor to GND |
| GPIO14 | Status LED, category 2 (Medium) | Through a 220 ohm resistor to GND |
| GPIO15 | Status LED, category 3 (High) | Through a 220 ohm resistor to GND |

The hardware plan's original pin table put the trigger button on GPIO0.
That pin is physically wired to the camera module's XCLK (clock) line on
every AI-Thinker ESP32-CAM board, so it cannot be used as a free digital
input once the camera is running, and must stay floating except for the
few seconds it is grounded to enter flashing mode. This mismatch was found
while writing the firmware (section 5.6) and an early draft of this report
moved the button to GPIO16 instead. Bring up on the real board then found a
second problem with GPIO16 itself, described in detail in section 5.6.1,
and the button was moved a second time, to its final position on GPIO13.
GPIO12 is a flash voltage strapping pin, but it boots correctly with a
status LED attached, because the LED and its resistor pull it to the same
logic level (LOW, 3.3 V flash) the board already expects at boot; this
behaviour was confirmed directly, since the Healthy category LED on GPIO12
is part of the firmware that has now been flashed and run.

{{TABLE:nano_pins|Arduino Nano pin usage.}}
| Nano pin | Connects to | Notes |
|---|---|---|
| 5V | LM2596 5 V output | Power in, about 50 mA |
| GND | Common ground bus | Shared with ESP32, relay and buck converter |
| D10 (SoftwareSerial RX) | ESP32-CAM GPIO1 (TX) | Receives the spray command line `S<ms>,<cat>` |
| D7 | Relay module IN | HIGH switches the relay on, which opens the solenoid |
| D13 | Onboard LED | Lights while the valve is open |

The relay's COM terminal connects to the battery positive terminal through
the inline fuse, and its NO (normally open) terminal connects to the
solenoid valve positive terminal, so the solenoid is off by default and
energises only while the relay is triggered.

## 5.4 POWER SYSTEM

Figure 5.2 shows the power distribution diagram. The 12 V battery pack feeds
the LM2596 buck converter, which is adjusted with its trim pot to exactly
5.00 V, measured with a multimeter under load, before any microcontroller is
connected (an overshoot at this step can destroy the ESP32-CAM or the Nano).
The regulated 5 V output feeds the ESP32-CAM, the Arduino Nano and the relay
module's logic side. The unregulated 12 V rail feeds the relay's switched side through the
inline 2 A fuse, and also feeds the pump directly. The hardware plan
originally called for a manual on or off toggle switch in series with the
pump. During assembly the team chose to leave this switch out and wire the
pump straight to the 12 V rail instead, so the pump runs continuously
whenever the battery is connected and stops only when the battery is
disconnected. This is a deliberate simplification, not an oversight: the
pump only pressurises the line, and it is the solenoid valve, gated by the
relay, that actually decides how much liquid reaches the nozzle, so a
separate pump switch adds a part without changing what the system actually
controls.

{{FIG:power_distribution|figures/fig_power_distribution.png|Power distribution diagram: battery, buck converter, 5V and 12V rails.}}

{{TABLE:power_budget|Approximate current draw per rail.}}
| Rail | Component | Approximate current |
|---|---|---|
| 5 V | ESP32-CAM, active WiFi and camera | about 300 mA |
| 5 V | Arduino Nano | about 50 mA |
| 5 V | Relay module | about 70 mA |
| 12 V | Pump, continuous | about 500 mA |
| 12 V | Solenoid, while open | about 300 mA |

Total current draw is approximately 1.2 A at 12 V. A fully charged 2,600 mAh
battery pack gives roughly two hours of continuous operation at this draw.
The actual battery voltage when fully charged cannot be measured until the
battery pack is assembled (section 5.11); a 3 x 18650 Li-ion pack of this
type is nominally 11.1 V and typically reads close to 12.6 V fully charged,
but the real reading from `HARDWARE_TEST_DATA.md` section A should replace
this expectation once the pack exists.

## 5.5 LIQUID PATH

Figure 5.3 shows the liquid path from the chemical tank to the nozzle. The
chemical tank outlet connects through silicone tubing to the pump inlet; the
pump outlet connects to the solenoid valve inlet; and the solenoid valve
outlet connects to the hollow cone nozzle. The pump runs continuously once
switched on, and the solenoid valve, not the pump, controls how much liquid
reaches the nozzle by opening only for the computed duration `ts`.

{{FIG:liquid_path|figures/fig_liquid_path.png|Liquid path diagram: tank, pump, solenoid valve, nozzle.}}

## 5.6 FIRMWARE BEHAVIOUR

The ESP32-CAM firmware (`esp32cam_sprayer.ino`, in
`Capstone/firmware/`, listed in full in Appendix 4) waits
for a trigger (a push button on GPIO13, an optional timer, or a remote
button on the Blynk dashboard), captures one 320 by 240 pixel frame through
the `esp_camera` driver, and sends the frame by HTTP POST to the Flask
`/predict` endpoint. Section 5.6.1 below explains why the frame is sent as
raw pixel data rather than as a JPEG image, and how the server side was
changed to accept it; this is the same request path already proven by the
project's own API integration tests (Chapter 8, section 8.3, case I11),
extended with two new query parameters. On receiving the JSON response, the
firmware reads `category_code` (0 for Healthy, 1 for Low, 2 for Medium, 3
for High) and `spray_time_s`, lights the matching status LED, pushes
severity and category figures to the Blynk dashboard over WiFi if the
dashboard is enabled in the firmware build (section 5.7), and sends a line
of the form `S<ms>,<cat>` over its serial TX pin (GPIO1) to the Arduino
Nano's SoftwareSerial RX pin (D10) at a baud rate of 9600, where `<ms>` is
the server's `spray_time_s` value converted to whole milliseconds and
`<cat>` is the category code carried along for logging on the Nano side.

Sending the already computed spray time, rather than only the 0 to 3
category code, is a deliberate design choice made while writing this
firmware. The effective coefficient `C_eff` that sets the spray time
(section 4.6) already includes the per disease factor from
`model/severity.py`; recomputing a spray time on the Nano from the category
code alone would silently drop that per disease scaling and could produce
a different, wrong duration from the one the server actually decided on.
Carrying the finished value forward keeps the dosing logic in exactly one
place, the Flask server, which is also the only place it is unit tested
(Chapter 8, section 8.2).

### 5.6.1 Real problems found during firmware bring up

Two genuine hardware problems were found only after the real ESP32-CAM
board was flashed, and both are reported here as found, since they are
useful, honest engineering findings and not something to hide.

The first problem is the GPIO16 pin conflict already mentioned in section
5.3. An earlier draft of the firmware moved the trigger button to GPIO16,
on the stated reasoning that GPIO16 "has no camera or SD card role on this
board and is always free". This reasoning turned out to be wrong. GPIO16
is the chip select line for the ESP32's onboard PSRAM (the extra memory
chip the camera driver needs for its frame buffer); the installed
development toolchain's own configuration file confirms this directly
(`CONFIG_D0WD_PSRAM_CS_IO=16`, and the paired clock line
`CONFIG_D0WD_PSRAM_CLK_IO=17`). Setting GPIO16 as a digital input for the
button silently disabled PSRAM, because the two uses conflict at the pin
level. Every memory allocation larger than 4 kilobytes is served from
PSRAM in this build configuration, so once PSRAM was disabled, the camera
driver's own frame buffer allocation began to fail, and the symptom on
the Serial Monitor was a generic crash (`Guru Meditation Error: Core 1
panic'ed (LoadProhibited)`) at camera start up, not an obvious "PSRAM is
off" message. The fix was to move the trigger button a second time, off
GPIO16 entirely and onto GPIO13 (Table 5.1), and to move the status LED
that previously used GPIO13 onto GPIO2 instead. Once the button was off
GPIO16, PSRAM came back and the camera, WiFi connection and API calls all
worked correctly in the same test session (section 5.8.2). GPIO16 and its
paired clock pin, GPIO17, must not be used for any other purpose on this
board, and this rule is now written directly into the firmware's own
comments so it is not lost again.

The second problem is that the specific camera module fitted to this board
does not support hardware JPEG encoding, even though the board is sold as
an OV2640 based AI-Thinker ESP32-CAM, the same part number the hardware
plan and section 5.6's original description assumed. Asking the camera
driver for `PIXFORMAT_JPEG` fails with a driver level error
("JPEG format is not supported on this sensor"). A small test sketch,
written to isolate the problem, confirmed that the same camera module
captures correctly in grayscale and in RGB565 pixel formats, so the sensor
itself and its ribbon connection are not faulty; only the JPEG path on this
particular unit fails. Encoding the raw frame into JPEG in software on the
ESP32 itself was tried next, and it ran out of usable memory on this board
(`JPG buffer malloc failed`, and in one configuration another
`LoadProhibited` crash) because the frame buffer and the software JPEG
encoder's own working memory could not both fit in the space available
once the earlier GPIO16 fix had moved the frame buffer back into PSRAM.
Rather than keep fighting the on device encoder, the firmware now captures
a 320 by 240 pixel RGB565 frame (153,600 bytes) and sends those raw pixel
bytes directly over HTTP, with no JPEG step on the ESP32 at all. The Flask
server (`app/server.py`) was extended with a small function,
`_pil_from_rgb565`, that decodes the raw big endian RGB565 bytes into a
normal colour image using numpy, before handing that image to the exact
same classification and severity measurement pipeline already used for
ordinary JPEG uploads from the web demo; the model, the segmentation
module and the dosing equations are completely unchanged, only the first
decoding step is different for this request path. The request carries two
new query parameters, `fmt=rgb565` and the frame width and height, so the
server knows to use this decoding path instead of its normal JPEG decoder.
A separate, smaller fix was needed alongside this one: the server's normal
JSON response includes a large base64 encoded mask image (`overlay_png`)
for the web demo, and the ESP32's own JSON parser ran out of memory trying
to hold a response that big (`NoMemory`). The server now skips this field
for ESP32 requests with a third query parameter, `overlay=0`, and the
firmware's own JSON buffer was also made larger, from 1,024 to 4,096
bytes, as a second layer of protection.

Taken together, these two findings mean that the capture resolution stated
earlier in some descriptions of this design, 640 by 480 pixels captured
and sent as JPEG, is not what the flashed and running firmware actually
does; the real, working design captures 320 by 240 pixels as raw RGB565
and decodes it on the server, as described above, and this is the version
that produced the real integration test result in section 5.8.2 and
Chapter 8, section 8.4.

The Arduino Nano firmware (`valve_controller.ino`, same folder, Appendix 4)
listens on its SoftwareSerial RX pin for a line starting with `S`, parses
the millisecond duration and the category code, and, if the duration is
greater than zero, drives D7 high to energise the relay and open the
solenoid for that duration, then drives D7 low again. A duration of 0
(Healthy) results in no actuation at all. A safety cap of 5,000
milliseconds, matching the hardware plan's own recommendation (section 11
of `hardware_implementation_plan.md`), clamps any longer request before it
reaches the relay, so a bad reading cannot empty the whole tank in one
cycle. The same firmware also accepts a single bare digit (0 to 3) typed
directly into its USB Serial Monitor as a bench test mode, so the relay and
solenoid wiring can be dry run with no camera, no WiFi and no API call at
all, exactly as described in the hardware plan's Phase 2 pairwise
integration step and in section 5.8 below.

Both `.ino` files have now been flashed onto a real ESP32-CAM and a real
Arduino Nano. The WiFi network name and password and the Flask `/predict`
URL placeholders inside `esp32cam_sprayer.ino` have been filled in with the
team's own values (section 5.8.2); the Blynk auth token is also filled in,
though `BLYNK_ENABLED` is currently 0 as explained in section 5.7. The
design value `QS_MLS_DESIGN` inside `valve_controller.ino` should still be
replaced with the measured flow rate once section 5.8.1 below has a real
number.

## 5.7 CLOUD API AND BLYNK DASHBOARD

The cloud inference server is a Flask application (`app/server.py`) exposing
a `/predict` endpoint that accepts a multipart image upload (used by the
web demo), ordinary JPEG bytes in the request body, or a raw RGB565 frame
with the `fmt=rgb565` query parameter (the form the ESP32-CAM firmware now
sends, section 5.6.1). The response JSON carries the disease class,
confidence, severity percentage, category, category code, base coefficient,
disease factor, effective (reduction) coefficient, dose per hill and valve
open time. During the bring up session reported in section 5.8.2, the
server was run directly on the team's own laptop and reached over a mobile
phone's personal WiFi hotspot, with the ESP32-CAM and the laptop joined to
the same hotspot network; this avoids the Colab and ngrok public URL that
changes on every restart, at the cost of needing the laptop and the
ESP32-CAM to be on the same local network. The ngrok and Colab path
described in the hardware plan (Table 10.1, Troubleshooting) remains
available as an alternative for a demonstration where the laptop cannot sit
on the same network as the sprayer.

The Blynk dashboard uses five virtual pin datastreams, matched one to one
with the fields the firmware already sends: V0 (severity, a gauge), V1
(category, a labelled value), V2 (chemical volume per cycle, a history
chart so usage over time is visible), V3 (an alert, shown as text) and V4
(a remote trigger button that the firmware's
`BLYNK_WRITE(VPIN_REMOTE_TRIGGER)` handler already listens for). The exact
template, datastream and widget configuration is written out in full in
`Capstone/firmware/BLYNK_SETUP.md`, so creating the
dashboard is a fill in the fields exercise rather than a design task.
Current Blynk IoT does not support an anonymous public link to a device
dashboard the way the original Blynk app once did; sharing a live device
view with someone else now means inviting their registered account into
the owning organisation, which is a different step from hosting a public
URL. The dashboard itself has been created, and Figure 5.4 is a screenshot
of it taken from the Blynk console, with the Severity gauge, Category,
Alert text, chemical usage chart and Remote Trigger button all visible and
populated. The firmware itself keeps the Blynk code path behind a single
build flag, `BLYNK_ENABLED`, and this flag is currently set to 0 in the
flashed and tested firmware (`esp32cam_sprayer.ino`), so the dashboard is
not being written to by the physical prototype at the time of writing this
report; the flag was turned off deliberately while isolating the two
problems in section 5.6.1, to reduce the number of things that could be
going wrong on the board at once, and it has not yet been turned back on
and re tested end to end. The dashboard connection, Blynk configuration and
virtual pin write calls are already written and unaffected by either of
the two fixes in section 5.6.1, so re enabling this flag and reflashing is
expected to be straightforward once it is prioritised.

{{FIG:blynk_dashboard|figures/ui_blynk_dashboard.png|PaddyGuard Blynk dashboard, showing the Severity gauge, Category, Alert, the chemical usage history chart and the Remote Trigger button, populated by the pipeline simulation replay.}}

The numbers on the dashboard in Figure 5.4 come from
`Capstone/firmware/push_to_blynk.py`, which replays the
project's own measured pipeline simulation (the same 49 image run reported
in Chapter 9) into these datastreams through Blynk's public HTTP API, one
reading every few seconds. This is stated plainly because it matters: the
screenshot shows the dashboard and its widgets genuinely working, but the
severity and category values on it are a replay of the software
simulation's real, already reported numbers, not live field telemetry from
the physical prototype, for the reason given directly above
(`BLYNK_ENABLED` is currently 0 in the flashed firmware). Once
`BLYNK_ENABLED` is set back to 1 and the ESP32-CAM is reflashed, the same
datastreams receive real field readings directly from
`Blynk.virtualWrite()` calls already written into `esp32cam_sprayer.ino`,
with no change to the dashboard itself; this is listed as a remaining item
in OPEN_ITEMS.md.

## 5.8 ASSEMBLY AND CALIBRATION PROCEDURE

The build follows seven phases, each one tested on its own before the next
begins, so that a wiring or firmware fault in one module does not get
confused with a fault in another.

1. **Procurement.** Order every part in the bill of materials (section 5.2)
   and check each against its specification when it arrives.
2. **Standalone bench tests.** Test the ESP32-CAM, the Arduino Nano, the
   relay module, the buck converter, and the pump and solenoid, one at a
   time, on USB power only, with no battery and no full wiring yet.
3. **Pairwise integration.** Connect the ESP32-CAM to the Arduino Nano over
   serial and confirm category codes are received correctly; connect the
   Nano to the relay and solenoid for a dry run with test durations; confirm
   the ESP32-CAM can reach the Flask API and parse the JSON reply; confirm
   the ESP32-CAM can update the Blynk dashboard.
4. **Power system assembly.** Build the battery pack, verify its voltage,
   wire it to the buck converter, and set the buck converter to exactly
   5.00 V under load before connecting any microcontroller.
5. **Full electrical integration.** Wire the complete signal chain on USB
   power first, confirm a full dry cycle (trigger to relay click), then
   switch to battery power and repeat the same test.
6. **Flow calibration.** With the pump running and the solenoid held open,
   collect the dispensed liquid for exactly 10 seconds into a measuring cup,
   three times, and average: `Qs = volume_mL / 10`. This is the one value in
   the dose equations (section 4.6) that must be measured rather than
   assumed, because it depends on the specific pump, solenoid and battery
   voltage used.
7. **End to end and field testing.** Run full cycles against printed or
   displayed images of each class, confirm the correct category lights and
   the correct volume sprays, and time the full cycle end to end. A field
   trial compares total chemical used in constant rate mode against
   variable rate mode on the same row, to check the chemical saving claim
   from Chapter 1 against a real measurement.

### 5.8.1 Measured flow rate and calibration result

The flow rate `Qs` has not yet been measured, because Phase 6, collecting
the dispensed liquid for a timed interval, has not been run with water in
the tank (section 5.8.2 below). This report therefore continues to use the
design value `Qs` = 3.5 mL/s from the hardware plan for all worked dose and
timing examples in Chapter 9, and labels every such example clearly as
calculated from the design value, not measured. This flow rate is only
used for the optional debug printout in `valve_controller.ino`
(`QS_MLS_DESIGN`); it does not affect the valve open time itself, because
`ts` arrives from the Flask server already computed (section 5.6), so
recalibrating `Qs` once a measured value exists means updating one
constant in the firmware comment rather than changing any timing logic.
Measuring `Qs` is listed in OPEN_ITEMS.md as the single most important
remaining hardware task, since every dose and timing figure in Chapter 9
depends on it being a real, measured number rather than the current design
assumption.

### 5.8.2 Bench and integration test results

Phases 1 to 3 of the procedure in section 5.8 have now been carried out on
the real boards, and the real results are reported here exactly as they
happened, including one honest caveat on the single integration cycle
described below. `Capstone/hardware_evidence/HARDWARE_TEST_DATA.md` still
holds the detailed, phase by phase sheet for Phases 4 to 7 (power system
assembly, full electrical integration on battery power, flow calibration,
and field testing), which had not been run at the time of writing this
report, and `Capstone/hardware_evidence/photos/` and `screenshots/` were
still empty, so no hardware photograph is shown in this chapter.

The Arduino Nano's relay and solenoid valve were bench tested completely
on their own, using the firmware's single digit test mode described in
section 5.6 (typing `0`, `1`, `2` or `3` into the Nano's own USB Serial
Monitor), with no camera, no WiFi and no ESP32-CAM connected at all. This
test confirms the relay and valve timing logic independently of the rest
of the system. The real Serial Monitor output from this test, exactly as
recorded, is reproduced below.

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

The relay was heard to click and the solenoid valve was seen to open and
close for the correct commanded duration on categories 1, 2 and 3, and
correctly did nothing on category 0. This confirms that the valve open and
close timing control works correctly in real hardware. The "expected
volume" figures printed above (4.38, 6.56 and 8.75 mL) use the design
value `QS_MLS_DESIGN` = 3.5 mL/s described in section 5.8.1, not a measured
flow rate, so they must be read as an expected volume at an assumed design
flow rate, pending the direct flow rate calibration in section 5.8.1, and
not as a measured dispensed volume. No water was run through the valve
during this bench test; it was a dry, relay click test only.

With the ESP32-CAM and Arduino Nano then wired together over the serial
link described in Table 5.1 and Table 5.2, one full automated cycle of the
assembled system was recorded, with the camera pointed at a leaf, the
ESP32-CAM connected to a mobile phone hotspot, and the Flask server running
on the team's laptop on the same hotspot network. The real Serial Monitor
output from the ESP32-CAM side of this cycle, exactly as recorded, is
reproduced below.

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

This single output shows the full signal chain working together in real
hardware for the first time: the camera captured a real frame, the WiFi
connection reached the laptop over the hotspot, the Flask server ran the
real trained classifier and the real severity measurement on that frame
and returned a result, the ESP32-CAM parsed that result without the
`NoMemory` error described in section 5.6.1, and it sent a real
`S2900,3` command on its serial line toward the Nano. The line
`cam_hal: EV-EOF-OVF` is a routine camera end of frame timing message from
the driver, not a failure; the correct 153,600 byte frame size and the
classification that follows show the capture succeeded. One honest caveat
belongs with this result: the `[cycle] triggered` line carries the exact
same timestamp as the `[boot] ready, waiting for trigger` line immediately
before it, which is the signature of the ESP32's GPIO13 pin floating
briefly at boot and being read as a button press, rather than a
deliberately timed physical press of the button by whoever was running the
test. The classification result itself is still genuine, real hardware
evidence, since a real frame was really captured, really classified by the
real server, and really turned into a real serial command; it should be
read as an automated bench and integration cycle of the fully assembled
system, not as a manually triggered field test, and this distinction is
kept throughout this report wherever this result is referred to (Chapter
8, section 8.4; Chapter 9).

{{TABLE:hardware_test_status|Hardware test status, updated with the real results above.}}
| Test phase | Status | Where the result is recorded |
|---|---|---|
| Standalone bench tests, ESP32-CAM camera, WiFi and API call | Done, passed (shown above) | This section |
| Standalone bench test, Nano relay and solenoid (dry, no water) | Done, passed (shown above) | This section, HARDWARE_TEST_DATA.md section B |
| Pairwise integration, ESP32-CAM to Nano serial link, one automated cycle | Done, passed, with the triggering caveat noted above | This section, HARDWARE_TEST_DATA.md section C |
| Blynk dashboard update from the physical prototype | NOT DONE, `BLYNK_ENABLED` is 0 (section 5.7) | HARDWARE_TEST_DATA.md section C |
| Flow calibration (measured Qs) | NOT DONE | HARDWARE_TEST_DATA.md section D |
| Spray volume check per category, with water | NOT DONE | HARDWARE_TEST_DATA.md section E |
| End to end cycle time, at least 10 runs | NOT DONE | HARDWARE_TEST_DATA.md section F |
| Class wise functional test | NOT DONE | HARDWARE_TEST_DATA.md section G |
| Full electrical integration on battery power (section 5.8, Phase 5) | NOT DONE, tested on USB power only so far | HARDWARE_TEST_DATA.md section C |
| Field trial (constant rate vs variable rate) | NOT DONE | HARDWARE_TEST_DATA.md section H |

### 5.8.3 Real problems faced and fixes

Section 5.6.1 above already describes the two most significant problems
found during this bring up session in full detail: the GPIO16 PSRAM chip
select conflict, and the camera module's lack of hardware JPEG support. A
third, smaller problem is worth recording here. The mobile phone used for
the WiFi hotspot has an apostrophe in its device name (for example,
"Sourish's iPhone"), and the character iOS inserts by default for this
apostrophe is not the plain keyboard apostrophe but a typographic
"curly" character; the ESP32's WiFi connection call needs an exact,
character for character match to the network name, so the firmware's
WiFi network name constant had to be written using the matching Unicode
character before the board would connect. The phone's Personal Hotspot
setting "Maximize Compatibility" also had to be turned on, since the
ESP32 cannot join a 5 GHz WiFi network and this setting forces the
hotspot to the 2.4 GHz band the ESP32 needs. Table 5.4 above and
`HARDWARE_TEST_DATA.md` section I should be updated as Phases 4 to 7 are
carried out.

## 5.9 KNOWN HARDWARE RISKS

Table 5.3 lists risks identified at the design stage, carried over from the
hardware plan's troubleshooting table, together with the mitigation already
built into the design.

{{TABLE:hardware_risks|Known hardware risks and mitigations, including two risks confirmed during real bring up (section 5.6.1, section 5.8.3).}}
| Risk | Mitigation |
|---|---|
| ESP32-CAM fails to flash | Hold GPIO0 to ground during upload, use a powered USB hub to avoid brownouts |
| GPIO16 (or GPIO17) used for any purpose other than PSRAM | Confirmed during bring up (section 5.6.1): never assign GPIO16 or GPIO17 to a button, LED or sensor on this board; the trigger button was moved to GPIO13 |
| Camera module cannot produce JPEG | Confirmed on this specific board (section 5.6.1): capture RGB565 instead and decode on the server with `_pil_from_rgb565`, rather than trying to encode JPEG on the ESP32 itself |
| WiFi will not connect to a phone hotspot | Confirmed during bring up (section 5.8.3): match the hotspot's exact SSID character for character, including any typographic apostrophe, and enable "Maximize Compatibility" for 2.4 GHz |
| Buck converter output drifts after handling | Re-measure under load with a multimeter before trusting it |
| Relay clicks but solenoid does not open | Check the solenoid is wired to NO, not NC; check for battery voltage sag under load |
| Inconsistent spray volume at the same `ts` | Battery voltage sag changes pump flow rate; recalibrate `Qs` at field voltage |
| Cloud API becomes unreachable | A laptop on the same WiFi hotspot as the ESP32-CAM avoids this (section 5.7); if using the ngrok and Colab path instead, update the URL in the firmware after every Colab restart |

## 5.10 CROSS CHECK WITH THE HARDWARE PLAN

Four points in the hardware plan do not match the software and firmware
that were actually built. First, the hardware plan specifies a MobileNetV2
classifier, but the model that was actually trained, evaluated and deployed
(Chapter 4, Chapter 6, Chapter 9) is EfficientNetV2-B0. This report follows
the code and the measured results, and uses EfficientNetV2-B0 throughout.
Second, the hardware plan's severity table uses the base paper's original
coefficients (0.33, 0.67, 1.00, with `ts = a / Qs`), while the deployed
`severity.py` module uses different base coefficients (0.30, 0.55, 0.80)
further scaled by a per disease factor, and a standardised valve open time
window instead of a direct divide by flow rate. This report follows the
deployed code as the implemented system (section 4.6) and states the base
paper's original coefficients separately wherever the base paper itself is
being discussed (Chapter 2, Chapter 9). Third, the hardware plan's pin
table (section 6.1 of `hardware_implementation_plan.md`) puts the trigger
push button on the ESP32-CAM's GPIO0 pin; writing the firmware (section
5.6) showed this is not workable, because GPIO0 is the camera module's
XCLK line on every AI-Thinker ESP32-CAM board and must stay free while the
camera runs. The button was moved to GPIO16 in an early draft of the
firmware, then moved a second time to its final position on GPIO13, after
real hardware bring up found that GPIO16 itself is the ESP32's PSRAM chip
select pin (section 5.6.1). Fourth, and found only during the same bring
up session, the physical camera module fitted to the team's ESP32-CAM does
not support hardware JPEG encoding, so the capture path described in an
earlier draft of this chapter, a 640 by 480 pixel JPEG captured and sent
directly from the ESP32, is not what the flashed firmware actually does;
the real, working firmware captures 320 by 240 pixels as raw RGB565 and
the Flask server decodes it (section 5.6.1). All four mismatches are
listed in OPEN_ITEMS.md for the team's awareness.

## 5.11 PROCUREMENT STATUS

The ESP32-CAM, its programmer board, the Arduino Nano, the relay module and
a 12 V DC solenoid valve have been purchased, and sections 5.6.1 and 5.8.2
report real bring up and bench test results on these parts. This is stated
plainly here because it directly explains why those sections could report
real results rather than NOT DONE for the first time in this report. The
remaining parts in the bill of materials (section 5.2), the pump, the
power pack, the buck converter, the spray nozzle, the tubing and the inline
fuse, had not been confirmed as purchased at the time of writing this
report, which is why sections 5.8.1 and the later rows of Table 5.4 still
report the flow calibration, the spray volume check with water, the full
battery powered run and the field trial as NOT DONE: those tests need the
liquid path and the battery pack assembled together, which has not
happened yet.

A search of aiiottech.in (Chennai), a general hobbyist electronics retailer
checked as a possible local source for these parts, found the Arduino
Nano, the 5 V optocoupler isolated relay module, the LM2596 buck converter,
18650 cells and holders, jumper wires and a breadboard in stock, but did
not stock a 12 V DC solenoid valve, a 12 V DC diaphragm pump, or an
agricultural spray nozzle; its only solenoid valve listing is rated for
230 V AC, which is the wrong class of part for this design, and its only
small pump in stock is a 5 V USB submersible pump rather than the 12 V,
higher pressure diaphragm pump the design needs. Its ESP32-CAM listings
were also out of stock at the time of checking. These three liquid path
parts, and a working ESP32-CAM, therefore still need to come from the
Amazon India search links already given in the bill of materials (section
5.2) or an equivalent agricultural or irrigation supplier, while the
electronics side of the bill of materials can be sourced from aiiottech.in
once the ESP32-CAM is back in stock there.
