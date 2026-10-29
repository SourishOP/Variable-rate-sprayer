# Open items for the team

Everything in this list is either a value only the team can supply, a
decision only the team can confirm, or a genuine mismatch between sources
that this report has recorded rather than silently picked a side on.
Nothing in the report invents a number to avoid this list.

## 1. Front matter and administrative details

- Guide's designation (for example, Associate Professor) and area of
  expertise: still a `[[ENTER ...]]` placeholder on the Certificate page.
- HoD name: still a `[[ENTER HOD NAME]]` placeholder on the Certificate page.
- Cover and title page month: currently set to November 2026; confirm this
  is the intended submission month before the final print.
- Actual amount spent on the hardware bill of materials, once procurement
  for the remaining parts (pump, battery pack, nozzle, tubing) is complete,
  to compare against the Rs. 2,250 to Rs. 2,400 planning estimate (Chapter
  5, section 5.2; Chapter 10, section 10.4).

## 2. Hardware evidence still genuinely missing

These are the items that real bring up work this session did **not**
produce, and the report keeps them as placeholders or NOT DONE rather than
guessing:

- **Measured flow rate, Qs.** The pump, solenoid and tubing have not been
  run through the timed collection procedure (hardware plan Phase 6,
  `HARDWARE_TEST_DATA.md` section D). Every mL and ts figure in Chapter 9,
  Table 9.1 still uses the unmeasured design value Qs = 3.5 mL/s. This is
  the single most important remaining hardware measurement, because it
  feeds directly into every dose and spray time number in the report.
- **Spray volume check with water.** No water has been run through the
  solenoid valve. Only a dry, no water relay and valve timing bench test
  has been done (Chapter 5, section 5.8.2; `HARDWARE_TEST_DATA.md` section
  E). The mL figures currently shown there are the firmware's own printed
  "expected volume at design Qs" figures, explicitly labelled as not
  measured.
- **Full battery powered run.** Both boards have been tested on USB power
  only. The battery pack, the buck converter and its 5.00 V trim have not
  yet been assembled or measured (`HARDWARE_TEST_DATA.md` sections A and
  B, LM2596 row).
- **End to end cycle timing over at least ten runs** (`HARDWARE_TEST_DATA.md`
  section F) and the **class wise functional test** (section G): not yet
  run. Only one automated integration cycle exists (see item 3 below).
- **Field trial comparing constant rate and variable rate chemical use**
  (`HARDWARE_TEST_DATA.md` section H): not yet run. The 40 to 43 percent
  chemical saving reported in Chapter 9 remains a software simulation
  figure on 49 test images, not a field measurement, and should not be
  read as equivalent to the base paper's field measured 33.88 percent.
- **Hardware photographs and screenshots.** `Capstone/hardware_evidence/
  photos/` and `screenshots/` are both still empty. No figure in this
  report claims to show a photograph of the assembled hardware.
- **Live Blynk dashboard from the physical prototype.** `BLYNK_ENABLED` is
  currently 0 in the flashed firmware (`esp32cam_sprayer.ino`). The Blynk
  dashboard screenshot in Chapter 5, Figure 5.4 is real, but its numbers
  are a replay of the software pipeline simulation through
  `push_to_blynk.py`, not live field telemetry. Re enable `BLYNK_ENABLED`,
  reflash, and confirm one real `Blynk.virtualWrite()` cycle before
  claiming the dashboard is live from the prototype.
- **Make and model of the solenoid valve and the pump.** The valve is
  recorded as a generic 12 V DC coil type unit (label reads "DC12V"); no
  exact make/model or datasheet was recorded. The pump's make and model
  are not yet recorded at all.

## 3. One real result with an honesty caveat the team should be aware of

The one recorded ESP32-CAM to Flask to Nano integration cycle (Chapter 5,
section 5.8.2; Chapter 8, section 8.4; Chapter 9) is genuine hardware
evidence: a real frame was captured, really sent over WiFi, really
classified by the real trained model, and a real serial command reached
the Nano. However, the `[cycle] triggered` line in that log has the exact
same timestamp as the "ready, waiting for trigger" line before it, which
is the signature of the GPIO13 button pin floating briefly at boot rather
than a deliberately timed physical button press. The report describes this
throughout as "an automated bench and integration cycle," never as a
manually triggered field test. If the team re runs this test with a
clearly observed, deliberate button press, that cleaner result should
replace this one and the caveat sentence can then be removed.

## 4. Design and documentation mismatches found and resolved this session

These are not missing data. Each one is a real mismatch between the
hardware plan or an earlier report draft and what was actually built or
found during bring up; this report follows the real, built system in every
case and records the mismatch here for the team's awareness.

- Trigger button pin: hardware plan says GPIO0 (not usable, it is the
  camera's XCLK line); an earlier firmware draft moved it to GPIO16 (also
  not usable, it is the ESP32's PSRAM chip select pin); the flashed and
  tested firmware uses GPIO13. The status LED that used to be on GPIO13
  (category 1, Low) was moved to GPIO2. See Chapter 5, sections 5.3, 5.6.1
  and 5.10, and `HARDWARE_TEST_DATA.md` section A.
- Camera capture format and resolution: an earlier description of this
  design assumed a 640 by 480 pixel JPEG captured and sent directly by the
  ESP32-CAM. The physical camera module on the real board has no hardware
  JPEG support; the flashed firmware captures 320 by 240 pixel raw RGB565
  instead and the Flask server decodes it. See Chapter 5, section 5.6.1;
  Chapter 3, section 3.5; Chapter 6, section 6.4.
- Manual pump switch: the hardware plan calls for a manual on or off
  toggle switch in series with the pump. The team chose to omit this part
  and wire the pump directly to the 12 V rail instead, since the solenoid
  valve, not the pump, is what actually gates the spray. This is recorded
  as a deliberate, valid simplification in Chapter 5, section 5.4, not as
  an error.
- Classifier architecture: hardware plan says MobileNetV2; the trained and
  deployed model is EfficientNetV2-B0 (Chapter 5, section 5.10; carried
  over from the previous drafting session, unchanged this session).
- Dosing coefficients: hardware plan and the base paper use C =
  0.33/0.67/1.00 with ts = a / Qs; the deployed `severity.py` uses C_base =
  0.30/0.55/0.80 scaled by a per disease factor and a standardised 0.5 to
  3.0 second window (Chapter 5, section 5.10; Chapter 9, section 9.6;
  carried over, unchanged this session).
- `Capstone/Test` folder naming: contains a "Neck Blast" folder (with a
  space) even though `class_names.txt` uses "Neck_Blast" (with an
  underscore); mapped correctly in the pipeline simulation script (carried
  over, unchanged this session).
- Six class merged dataset size: `results/RESULTS.md` states 4,242 images;
  the notebook's own merge cell counts 4,297; both numbers are reported,
  the discrepancy is not resolved (carried over, unchanged this session).
- PlantSeg dataset licence: `results/RESULTS.md` and the hardware plan
  state CC BY; the PlantSeg paper's own licence line reads CC BY-NC-ND 4.0
  (carried over, unchanged this session).
- Oberti et al. and Esau et al. publication years: corrected to 2016 and
  2013 respectively against each paper's own front matter, where earlier
  deck slides used different years (carried over, unchanged this session).

## 5. Known limitation, not a missing item

The classifier's two thinnest classes, Bacterial_Blight and Leaf_Smut (55
training images each), remain the main source of weaker, less reliable
predictions throughout Chapter 9. This is a data limitation, not a hardware
or firmware problem, and the recommended fix (collecting more images for
these two classes) is already stated as the top priority in Chapter 10,
section 10.7.
