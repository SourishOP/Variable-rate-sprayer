# Hardware Implementation Plan
## Deep Learning & IoT-Based Real-Time Variable-Rate Chemical Spraying System for Disease Control in Paddy Crop

This is a complete, self-contained hardware reference for the physical build.
It assumes the software (CNN model, Flask/ngrok inference API, ESP32-CAM
firmware, Arduino Nano firmware, Blynk dashboard) is already written and
tested in isolation. The goal here is to go from loose components to a
working, calibrated physical prototype without having to debug firmware and
hardware at the same time.

**Build order matters:** bench-test each module alone → wire two modules at a
time → build the power rail → integrate everything electrically → calibrate
the liquid path → end-to-end test → field test. Do not wire the full system
on day one.

**Total hardware budget: ~₹2250-2400 (under ₹2500 target).**

---

## 1. Project context (for anyone picking up this doc)

- **Base paper:** Tewari et al. (2020), *Image processing based real-time
  variable-rate chemical spraying system for disease control in paddy crop*,
  Artificial Intelligence in Agriculture, 4, 21-30.
- **What the base paper did:** captured paddy plant images with webcams +
  laptop, used chromatic aberration (CA) thresholding to find diseased regions,
  computed disease severity, and opened solenoid valves for a calculated
  duration to spray a variable amount of agrochemical. Achieved a minimum
  **33.88% reduction** in chemical use (VRA vs constant-rate).
- **Our novelty (what this hardware supports):**
  1. **CNN (MobileNetV2) deep learning** replaces CA thresholding — more robust
     across lighting, generalizes to multiple diseases.
  2. **ESP32-CAM + cloud inference** replaces the laptop + MATLAB — compact,
     low-cost, portable.
  3. **Blynk IoT dashboard** for remote monitoring of severity, chemical usage,
     alerts, and remote spray triggering.
  4. **4-level severity** including a **Healthy = zero-spray** category, so no
     chemical is wasted on healthy plants (the base paper always sprayed at
     least 33%).
- **Target crop / classes:** Paddy / Rice — Healthy, Bacterial Blight,
  Brown Spot, Leaf Smut.
- **Compute choice:** Cloud inference (Google Colab + Flask + ngrok). Needs
  WiFi / mobile hotspot in the field.
- **Team:** Sourish Das, Aditya Singh.

---

## 2. System architecture (operational flow)

```
[ESP32-CAM] --capture JPEG--> WiFi --HTTP POST--> [Google Colab Flask + MobileNetV2 CNN]
                                                              |
                                              disease class + severity % (JSON)
                                                              |
[Blynk Dashboard] <--WiFi-- [ESP32-CAM] <--HTTP response-----+
                                   |
                           Serial (category code 0-3)
                                   v
                            [Arduino Nano] --computes ts--> [Relay] --> [12V Solenoid Valve] --> [Nozzle] --> spray
                                   ^
                           [12V battery] --> pump (always on) ; --> LM2596 buck --> 5V to MCUs
```

Step-by-step cycle:

1. Trigger (push button on ESP32, timed interval, or Blynk remote button).
2. ESP32-CAM captures a 640×480 (VGA) JPEG.
3. ESP32 sends the JPEG via HTTP POST to the Colab Flask server (ngrok URL),
   endpoint `/predict`.
4. MobileNetV2 classifies the image, returns JSON:
   `{disease_class, confidence, severity_percent, category, reduction_coefficient, category_code}`.
5. ESP32 maps the result to a category code (0=Healthy, 1=Low, 2=Medium, 3=High)
   and sends that single byte to the Arduino Nano over serial.
6. Arduino Nano computes the solenoid open duration `ts` and actuates the relay
   → solenoid for that duration (no actuation for Healthy).
7. ESP32 simultaneously pushes severity, chemical amount, and alerts to Blynk,
   and lights the matching status LED.
8. System waits for the next trigger. Full cycle target: **< 5 seconds.**

---

## 3. Severity mapping and spray equations

### 3.1 Four-level severity (our modification of the paper's 3 levels)

| Category | Disease severity (S) | Reduction coefficient (C) | Category code | Action |
|---|---|---|---|---|
| Healthy | 0% (CNN "Healthy" class) | 0.00 | 0 | No spray (novel) |
| Low | 0.1 – 5% | 0.33 | 1 | Light spray |
| Medium | 5.1 – 20% | 0.67 | 2 | Medium spray |
| High | 20.1 – 100% | 1.00 | 3 | Full spray |

The base paper assigned 33% of the recommended rate as the base dose for Low
(0-5%), 67% for Medium (5.1-20%), and 100% for High (20.1-100%). We keep those
three coefficients and add Healthy (C=0.00) so healthy plants receive zero
chemical.

### 3.2 Spray duration equations (from the base paper, Eqs. 4 & 5)

```
a  = (C × A) / (d × 10)      # required chemical per hill, mL/hill
ts = a / Qs                  # solenoid open duration, seconds
```

Where:
- `a`  = required amount of agrochemical per hill (mL/hill)
- `C`  = reduction coefficient (0.00 / 0.33 / 0.67 / 1.00 — see table above)
- `A`  = recommended application rate of agrochemical (L/ha) — default 500
- `d`  = hill density (hills/m²) — default 25
- `ts` = solenoid valve open duration (seconds)
- `Qs` = flow rate of liquid through the solenoid (mL/s) — **measured during
         calibration (Phase 5); this is the one value you must determine
         empirically.**

### 3.3 Worked examples (with A=500, d=25, Qs≈3.5 mL/s)

| Category | C | a = (C×A)/(d×10) | ts = a/Qs |
|---|---|---|---|
| Healthy | 0.00 | 0.000 mL/hill | 0.000 s |
| Low | 0.33 | 0.660 mL/hill | 0.189 s |
| Medium | 0.67 | 1.340 mL/hill | 0.383 s |
| High | 1.00 | 2.000 mL/hill | 0.571 s |

These `ts` values are examples — recompute them in the Arduino firmware after
you measure the real `Qs` for your pump + solenoid + battery-voltage combination.

---

## 4. Complete Bill of Materials (with model names and links)

Amazon India links are given as search links because exact product URLs change
frequently. Verify the specific spec column when the part arrives.

| # | Component | Specific model / spec | Purpose | Approx ₹ | Link |
|---|---|---|---|---|---|
| 1 | ESP32-CAM | AI-Thinker ESP32-CAM with OV2640 (2MP, WiFi+BT, microSD slot, 4MB PSRAM) | Image capture + WiFi + cloud comm + Blynk | 450-550 | https://www.amazon.in/s?k=AI+Thinker+ESP32-CAM+OV2640 |
| 2 | ESP32-CAM programmer | ESP32-CAM-MB (USB micro-B, CH340 chip) | Upload firmware to ESP32-CAM | 150-200 | https://www.amazon.in/s?k=ESP32-CAM-MB+programmer |
| 3 | Arduino Nano | Arduino Nano V3.0 ATmega328P CH340 (clone, mini USB) | Valve timing / relay control | 200-280 | https://www.amazon.in/s?k=Arduino+Nano+V3+CH340 |
| 4 | Solenoid valve | 12V DC 1/2" Normally Closed (NC) plastic solenoid valve, 0.02-0.8 MPa | Flow control (opens for ts seconds) | 250-400 | https://www.amazon.in/s?k=12V+solenoid+valve+normally+closed+1%2F2+inch |
| 5 | Relay module | 5V 1-channel relay module with optocoupler (Songle SRD-05VDC-SL-C) | Switch 12V solenoid from 5V logic | 45-70 | https://www.amazon.in/s?k=5V+1+channel+relay+module+optocoupler |
| 6 | Water pump | 12V DC mini diaphragm pump (R385 type, 1.5-2 L/min, self-priming) | Maintain liquid flow/pressure | 200-350 | https://www.amazon.in/s?k=R385+12V+diaphragm+water+pump |
| 7 | Power | 3× 18650 Li-ion (3.7V, 2600mAh) + 3-cell holder (~11.1V), OR 12V 2A sealed lead-acid | 12V source | 300-450 | https://www.amazon.in/s?k=18650+battery+holder+3+cell |
| 8 | Buck converter | LM2596 DC-DC step-down module (adjustable, 12V→5V, has trim pot) | Regulate 12V down to 5V for MCUs | 45-70 | https://www.amazon.in/s?k=LM2596+adjustable+buck+converter |
| 9 | Spray nozzle | Adjustable brass mist nozzle (1/4" thread, hollow-cone pattern, 60-80°) | Spray pattern onto plant | 80-150 | https://www.amazon.in/s?k=brass+adjustable+mist+spray+nozzle+1%2F4 |
| 10 | Silicone tubing | 6mm ID × 8mm OD food-grade silicone tube (≥1 m, buy 2 m) | Liquid path tank→pump→valve→nozzle | 60-100 | https://www.amazon.in/s?k=6mm+silicone+tube+food+grade |
| 11 | Jumper wires + breadboard | Male-Female + Male-Male kit (40-pin each) + mini breadboard | Prototyping connections | 100-150 | https://www.amazon.in/s?k=jumper+wires+breadboard+kit |
| 12 | Push button | 12mm momentary push button | Manual capture/spray trigger | 10-20 | https://www.amazon.in/s?k=12mm+momentary+push+button |
| 13 | Inline fuse (recommended) | 2A blade fuse + inline holder | Protect boards from wiring mistakes | ~30 | https://www.amazon.in/s?k=inline+blade+fuse+holder |
| — | Multimeter (if needed) | Any basic DC voltage + continuity meter | Buck calibration, wiring checks | — | https://www.amazon.in/s?k=digital+multimeter |

### Budget summary

| Category | Cost range (₹) |
|---|---|
| Core electronics (ESP32-CAM + programmer + Nano + relay + buck) | 900-1170 |
| Actuators (solenoid + pump) | 450-750 |
| Power (batteries/holder + fuse) | 330-480 |
| Plumbing (nozzle + tubing) | 140-250 |
| Misc (wires, button, breadboard) | 110-170 |
| **Total** | **~₹1930-2720 (target build ≈ ₹2250-2400)** |

### Optional upgrades (only if budget/time allows later)

| Component | Model | Purpose | Approx ₹ |
|---|---|---|---|
| OLED display | 0.96" SSD1306 I2C | Show severity/category on the device itself | 150 |
| Ultrasonic sensor | HC-SR04 | Detect plant presence / distance to trigger capture | 80 |
| Second solenoid + relay | same models as #4, #5 | Two-row coverage (like the base paper's 2 nozzles) | 400 |
| Weatherproof enclosure | IP65 box | Field protection for electronics | 200 |
| Battery charger | TP4056 module | Recharge 18650 cells over USB | 40 |

---

## 5. Component notes and gotchas

- **ESP32-CAM (AI-Thinker):** built-in WiFi (802.11 b/g/n) is essential for
  cloud inference and Blynk. OV2640 can do up to 1600×1200; we use 640×480 (VGA)
  for faster upload. 4MB PSRAM holds the image buffer. After camera init, only a
  few GPIOs remain free for button/LEDs — plan pin usage carefully (see §6).
  These boards are notorious for flaky USB-serial — if upload fails, hold IO0 to
  GND during flashing and use a powered USB hub to avoid brownouts.
- **Arduino Nano:** receives the severity code via **SoftwareSerial** (pins D10
  RX, D11 TX) so the hardware serial (pins 0/1) stays free for USB debugging.
  D7 drives the relay, D13 is the onboard status LED. If upload fails, select
  "ATmega328P (Old Bootloader)" in the Arduino IDE (common on CH340 clones).
- **Solenoid valve (12V NC):** Normally Closed means no power = no flow (safe
  default). Place it **upstream** of the nozzle so it gates the chemical.
  Response time ~30-50 ms, fine for this application. Confirm it's rated for
  liquid, not air-only.
- **R385 diaphragm pump:** self-priming (can draw from a tank below it),
  ~1.5-2 L/min. Runs continuously during operation via a manual switch; the
  solenoid (not the pump) does the metering.
- **LM2596 buck converter:** buy the **adjustable** version with a trim pot.
  Set output to exactly 5.00V with a multimeter **before** connecting any board.
  Overshoot can destroy the ESP32-CAM and Nano.
- **Relay module:** use the optocoupler-isolated type to protect the Arduino
  from the 12V switching side. Solenoid connects to **COM + NO** (so it's off by
  default and energizes when the relay triggers).

---

## 6. Detailed pin-by-pin wiring

### 6.1 ESP32-CAM pin usage

| ESP32-CAM pin | Connects to | Notes |
|---|---|---|
| 5V | LM2596 5V output | Power in (~300 mA active) |
| GND | Common ground bus | Must share GND with Nano, relay, buck |
| GPIO1 (U0TXD) | Arduino Nano D10 (SoftwareSerial RX) | Serial data out (category code). Disconnect while flashing. |
| GPIO0 | Push button → GND | Manual trigger. Also used for flashing (hold to GND to enter flash mode) |
| GPIO12 | Green LED → 220Ω → GND | Status: Healthy |
| GPIO13 | Yellow LED → 220Ω → GND | Status: Low |
| GPIO14 | Orange LED → 220Ω → GND | Status: Medium |
| GPIO15 | Red LED → 220Ω → GND | Status: High |

> Note: exact status-LED GPIOs can be changed in firmware; GPIO12-15 are a
> reasonable free set after camera init. If you hit boot issues, GPIO12 and
> GPIO15 are strapping pins — if the board won't boot with LEDs attached, move
> the LEDs to other free GPIOs and update the firmware.

### 6.2 Arduino Nano pin usage

| Nano pin | Connects to | Notes |
|---|---|---|
| 5V | LM2596 5V output | Power in (~50 mA) |
| GND | Common ground bus | Shared with ESP32, relay, buck |
| D10 (SoftwareSerial RX) | ESP32-CAM GPIO1 (TX) | Receives category code '0'-'3' |
| D11 (SoftwareSerial TX) | (optional, unused) | Reserved for future two-way comms |
| D7 | Relay module IN | HIGH = relay on = solenoid open |
| D13 | Onboard LED | Spray-active indicator |

### 6.3 Relay module

| Relay pin | Connects to | Notes |
|---|---|---|
| VCC | LM2596 5V output | Relay coil/logic power (~70 mA) |
| GND | Common ground bus | |
| IN | Arduino Nano D7 | Control signal |
| COM | 12V battery (+) via inline fuse | Switched 12V input |
| NO (Normally Open) | Solenoid valve (+) | Energized only when relay triggers |
| NC (Normally Closed) | — | Leave unconnected |

### 6.4 Actuation / liquid path

| Connection | From | To |
|---|---|---|
| Solenoid power | Relay NO | Solenoid (+) |
| Solenoid return | Solenoid (−) | 12V battery (−) |
| Pump power | 12V battery (via manual ON/OFF switch) | Pump (+/−), runs continuously |
| Liquid: tank → pump | Chemical tank outlet | Pump inlet (6mm silicone tube) |
| Liquid: pump → valve | Pump outlet | Solenoid valve inlet (6mm tube) |
| Liquid: valve → nozzle | Solenoid valve outlet | Hollow-cone nozzle inlet |

### 6.5 Power distribution

| Rail | From | To |
|---|---|---|
| Buck input | 12V battery (+/−) via fuse | LM2596 VIN+ / VIN− |
| 12V branch A | Battery (+) via switch | Pump |
| 12V branch B | Battery (+) via fuse | Relay COM |
| 5V branch 1 | LM2596 5V out | ESP32-CAM 5V |
| 5V branch 2 | LM2596 5V out | Arduino Nano 5V |
| 5V branch 3 | LM2596 5V out | Relay VCC |
| Common ground | All GND pins (ESP32, Nano, relay, buck −, battery −) | Tied together on one bus |

### 6.6 Consolidated wiring reference (quick table)

| Connection | From | To |
|---|---|---|
| Serial data | ESP32-CAM GPIO1 (TX) | Arduino Nano D10 (SoftwareSerial RX) |
| Relay control | Arduino Nano D7 | Relay IN |
| Relay power | 12V battery (+) via fuse | Relay COM |
| Solenoid | Relay NO | Solenoid (+) |
| Solenoid return | Solenoid (−) | 12V battery (−) |
| Pump | 12V battery (via switch) | Pump (+/−) |
| ESP32 power | LM2596 5V out | ESP32-CAM 5V pin |
| Nano power | LM2596 5V out | Nano 5V pin |
| Relay logic power | LM2596 5V out | Relay VCC |
| Buck input | 12V battery via fuse | LM2596 VIN |
| Trigger button | ESP32 GPIO0 | Button → GND (internal pull-up) |
| Status LEDs | ESP32 GPIO12/13/14/15 | LED → 220Ω → GND |
| Common ground | All GND pins | Tied together |

### 6.7 Power budget (sanity check)

| Rail | Component | Approx current |
|---|---|---|
| 5V | ESP32-CAM (active WiFi + camera) | ~300 mA |
| 5V | Arduino Nano | ~50 mA |
| 5V | Relay module | ~70 mA |
| 12V | Pump (continuous) | ~500 mA |
| 12V | Solenoid (while open) | ~300 mA |

Total ≈ 1.2 A @ 12V. A 2600 mAh pack gives roughly 2 hours of continuous
operation. Size the inline fuse at 2A.

---

## 7. Build phases

### Phase 0 — Procurement (Day 1-3)

Order everything in the BOM (§4). When parts arrive, verify each against its
"spec" column. **Order spares for the two cheapest, most failure-prone parts:**
an extra relay module (₹50) and an extra push button — a dead ₹50 part should
never block you for a week.

### Phase 1 — Standalone bench tests (Day 4-6)

Test every module **before** anything is wired together. Each test uses only
USB power from your laptop — no battery, no solenoid yet.

1. **ESP32-CAM alone**
   - Flash a basic "blink + `Serial.println`" sketch first to confirm the board
     and CH340 driver work (hold IO0 to GND during flashing if upload fails;
     use a powered USB hub to avoid brownouts).
   - Then flash the `CameraWebServer` example to confirm the OV2640 ribbon is
     seated and you can view a live stream in a browser on your WiFi.
2. **Arduino Nano alone**
   - Flash a D13 blink sketch to confirm the board and bootloader.
   - Flash a sketch that toggles D7 HIGH/LOW every second; verify with a
     multimeter or an LED+resistor on D7 that the pin actually switches.
3. **Relay module alone**
   - Power VCC/GND from Arduino 5V/GND. Drive IN from D7 (blink sketch).
   - Confirm you hear the relay click and COM-NO continuity closes (multimeter
     continuity mode) when D7 is HIGH.
4. **Buck converter alone**
   - Power LM2596 input from the 18650 pack (or bench 12V). Adjust the trim pot
     while measuring output until it reads exactly **5.00V**. Do this before
     connecting any board — overshoot can fry the ESP32 and Nano.
5. **Pump + solenoid in a bucket (no spraying yet)**
   - Power the pump directly from the battery through a switch; draw water from
     a bucket and confirm it primes into a second bucket.
   - Wire the solenoid in-line between pump output and a short tube. Power the
     solenoid directly (bypass relay) and confirm NC behavior: no power = no
     flow, powered = flow.

Do not proceed until every item passes individually.

### Phase 2 — Pairwise integration (Day 7-9)

1. **ESP32-CAM ↔ Arduino Nano serial link**
   - Wire ESP32 GPIO1 (TX) → Nano D10 (SoftwareSerial RX), common GND.
   - Minimal ESP32 sketch sends `'0'/'1'/'2'/'3'` every 2 s; minimal Nano sketch
     `Serial.println`s whatever it receives, viewed on the Nano's hardware
     Serial Monitor.
   - **Important:** connect GPIO1 to the Nano only after the ESP32 is flashed
     and running standalone (unplugged from the programmer), or you'll get
     upload conflicts.
2. **Nano ↔ Relay ↔ Solenoid (dry run, no water)**
   - Feed the Nano test codes '0'-'3' via Serial Monitor; confirm the relay
     clicks for different hardcoded durations (dummy ts, e.g. 0/0.5/1.0/1.5 s)
     — verifies control logic independent of the real equation.
3. **ESP32-CAM ↔ WiFi ↔ Flask API**
   - Point the ESP32 sketch at your running Colab ngrok URL; trigger a capture;
     confirm the HTTP POST succeeds and JSON parses on Serial Monitor — no
     Arduino/relay involved yet.
4. **ESP32-CAM ↔ Blynk**
   - Confirm virtual-pin updates appear in the Blynk app from a standalone
     sketch before combining with camera/HTTP logic.

### Phase 3 — Power system assembly (Day 10)

1. Assemble the 3×18650 pack, check polarity, measure voltage (~11.1-12.6V).
2. Wire battery → LM2596 input; re-verify 5.00V **under load** (with an LED or
   resistor, not just an unloaded multimeter).
3. Build distribution per §6.5: 12V to pump switch, 12V to relay COM, 5V to
   ESP32, 5V to Nano, 5V to relay VCC.
4. Add the inline **2A fuse** on the 12V battery output.

### Phase 4 — Full electrical integration (Day 11-12)

1. With everything still on USB power (not battery), wire the complete signal
   chain: ESP32 → Nano → Relay → (dry) Solenoid per §6.6.
2. Confirm the full dry cycle: button press → capture → cloud inference →
   category code → Nano computes `ts` → relay clicks for the right duration.
3. Only after the dry run works, switch from USB to the 12V battery + buck and
   re-run the same test.
4. Mount solenoid, pump, and nozzle on the frame/cart with real tubing, but
   still spray into a measuring container, not onto plants.

### Phase 5 — Flow calibration (Day 13)

Determines `Qs` (mL/s), the one empirical constant the spray-duration equation
depends on. Pump running continuously, solenoid held open (bypass timing):

1. Open the solenoid for exactly 10 seconds into a measuring cup.
2. `Qs = volume_mL / 10`.
3. Repeat 3× and average — flow varies with battery voltage sag, so measure
   with a reasonably charged pack.
4. Update `Qs` in the Arduino Nano firmware.
5. Re-run a dry calibration check: command a known category (e.g. Medium,
   C=0.67) and verify the dispensed volume over `ts` matches the expected `a`
   (mL/hill) within ~10%.

### Phase 6 — End-to-end system test (Day 14)

1. Mount the camera facing the target; position the nozzle ~0.25 m ahead of the
   camera's field of view (matching the base paper's lag compensation).
2. Run full cycles against printed/displayed images of each class and confirm:
   - Correct classification appears on Blynk
   - Correct category LED lights
   - Correct spray volume is dispensed (measure it)
   - Healthy triggers zero spray
3. Time the full cycle (capture → inference → spray): target < 5 s. If
   ngrok/Colab inference is slow, note it as a known limitation rather than
   over-engineering around it.

### Phase 7 — Field testing (Day 15-17)

1. Test outdoors under real sunlight — verify image quality isn't washed out.
   If it is, add a simple shade hood over the camera (the base paper used a
   green-cloth covering for the same reason).
2. Run comparative trials: the same row in constant-rate mode (relay open a
   fixed duration) vs variable-rate mode; measure total chemical used in each to
   reproduce the paper's ~33.88% saving comparison.
3. Log at least 15-20 spray cycles across severities for the results section.

---

## 8. Tools you'll need on hand

- Multimeter (continuity + DC voltage)
- Small Phillips screwdriver set
- Wire strippers, soldering iron + solder (for perfboard connections)
- Hot-glue gun or cable ties (securing tubing and wiring on the frame)
- A measuring cup graduated in mL (for Qs calibration)
- A second phone/laptop to watch Blynk and the Serial Monitor at once

---

## 9. Safety notes

- Keep all 12V wiring away from the water path — a leak near an exposed solder
  joint is the most likely failure mode. Heat-shrink or hot-glue every exposed
  connection near the pump/solenoid.
- Use plain water for all calibration and dry-run testing. Load actual
  agrochemical only once the full cycle is verified and you're ready for field
  trials, and follow label PPE guidance (gloves, no ingestion/inhalation).
- Keep the inline 2A fuse on the 12V rail — the cheapest protection against a
  wiring mistake during assembly.
- Set the buck converter to 5.00V and confirm with a multimeter before
  connecting the ESP32-CAM or Nano; overshoot destroys both.

---

## 10. Troubleshooting

| Symptom | Likely cause |
|---|---|
| ESP32-CAM won't flash | IO0 not grounded during upload; brownout from a weak USB port — use a powered hub |
| ESP32-CAM won't boot with LEDs attached | GPIO12/GPIO15 are strapping pins — move those LEDs to other free GPIOs |
| Nano won't upload | Select "ATmega328P (Old Bootloader)" in Arduino IDE (CH340 clones) |
| Nano doesn't receive serial data | Common GND missing between boards; wrong RX/TX pin; baud mismatch |
| Relay clicks but solenoid doesn't open | Solenoid wired to NC instead of NO; insufficient 12V current (battery sag under load) |
| Buck converter output drifts | Trim pot moved during handling; re-measure under load before trusting it |
| Pump primes but no pressure at nozzle | Air leak in tubing joints; nozzle orifice clogged; valve still partially closed |
| Inconsistent spray volume at same `ts` | Battery voltage sag changes pump flow rate — recalibrate `Qs` at the voltage you'll field-test at |
| ngrok URL stopped working | Colab session expired — restart the Colab notebook, get the new URL, update it in the ESP32 firmware |

---

## 11. Firmware constants to set (cross-reference for the software folder)

When you wire the hardware, these values in the firmware must match the physical
build:

**Arduino Nano (`arduino_nano/valve_controller.ino`):**
- `A` = 500 (L/ha) — recommended application rate
- `d` = 25 (hills/m²) — planting density
- `Qs` = **measured in Phase 5** (mL/s) — update after calibration
- `RELAY_PIN` = D7
- SoftwareSerial RX = D10, TX = D11
- Safety cap on max solenoid open time (e.g. 5 s) so a bad reading can't dump
  the whole tank

**ESP32-CAM (`esp32cam/esp32cam_sprayer.ino`):**
- WiFi SSID / password
- ngrok `/predict` URL (changes each Colab session)
- Blynk auth token / template ID
- Status-LED GPIOs (12/13/14/15) and button GPIO (0)
- Serial TX pin to Nano = GPIO1, baud 9600 (match the Nano's SoftwareSerial)
