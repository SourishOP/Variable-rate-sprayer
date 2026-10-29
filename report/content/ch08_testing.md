# TESTING

## 8.1 TESTING STRATEGY

The system was tested at four levels. Unit tests check the severity and
dosing logic in `model/severity.py` in isolation, with known inputs and
known expected outputs. Integration tests check the Flask API end to end,
including real image uploads and real model inference. A pipeline
simulation runs the complete decision chain, classification, segmentation,
severity, dosing, on a real set of test images, to see how the whole system
behaves together rather than one module at a time. Hardware bench, field
and system tests check the physical prototype, and are reported from the
team's own measured hardware evidence where it is available (Chapter 5).

## 8.2 UNIT TESTS

Thirty seven unit test cases were written and run against the real
`model/severity.py` code (`report/build/run_unit_tests.py`,
results saved in `report/content/unit_test_results.json`). All 37
cases passed. The cases are grouped as follows.

{{TABLE:unit_test_summary|Unit test case groups and results.}}
| Group | What is checked | Cases | Result |
|---|---|---|---|
| Category mapping | Severity percentage maps to the correct category and base coefficient at and around each threshold (0, 0.1, 5.0, 5.1, 20.0, 20.1, 100.0 percent) | 7 | 7/7 passed |
| Disease factor | The correct scaling factor is returned for every known class name, and a sensible default for an unknown class name | 9 | 9/9 passed |
| Guards | The severity floor correctly forces Healthy below 1.5 percent and keeps a disease label at exactly 1.5 percent; the confidence gate correctly flags below 0.70 and does not flag at or above 0.70; the effective coefficient is correctly clamped and correctly computed for two worked examples | 8 | 8/8 passed |
| Spray time | The timing function returns correct values at each coefficient boundary (0.00, 0.30, 0.55, 0.80, 1.00, 1.50, negative), never decreases as the coefficient increases, and always stays inside the 0.5 to 3.0 second window when non zero | 9 | 9/9 passed |
| Segmentation (colour method) | The classical colour based severity method measures a drawn test patch within a close tolerance of its known area, and reports close to 0 percent on a plain, undamaged leaf | 3 | 3/3 passed |
| Output fields | The prediction dictionary always carries all ten expected fields | 1 | 1/1 passed |

Two representative worked examples from the Guards and Spray time groups
illustrate how the equations behave: a High severity Neck_Blast leaf (base
coefficient 0.80, disease factor 1.25) gives an effective coefficient
clamped at 1.00 and a spray time of 3.0 seconds (the maximum of the valve
window); a Low severity Leaf_Smut leaf (base coefficient 0.30, disease
factor 0.80) gives an effective coefficient of 0.24 and a spray time of
1.1 seconds.

## 8.3 API INTEGRATION TESTS

Thirteen integration test cases were run against the real Flask test client
(`report/build/run_api_tests.py`, results in
`report/content/api_test_results.json`). All 13 cases passed, with a
median response time of 757.8 ms, a minimum of 396.1 ms and a maximum of
4,487.9 ms (the slowest case was the first call in the run, which includes a
one time model warm up cost).

{{TABLE:api_test_summary|API integration test cases and results.}}
| ID | What is checked | Result |
|---|---|---|
| I1, I2 | `/health` returns status ok, the inference mode, and lists all six classes | Passed |
| I3 | `/` serves the web demo page as HTML | Passed |
| I4, I5 | `/predict` without an image, or with bytes that are not an image, is rejected with a 400 response | Passed |
| I6 to I10 | Multipart upload of one real sample image from each of five classes (Bacterial_Blight, Brown_Spot, healthy, leaf_smut, Neck Blast) returns a 200 response with every expected field present | Passed, response times 396 ms to 4,488 ms |
| I11 | Raw image bytes in the request body, the form the ESP32-CAM sends, are accepted | Passed |
| I12 | Query parameters A, d and Qs correctly change the computed dose per hill | Passed |
| I13 | `spray_time_s` stays at 0 or inside the 0.5 to 3.0 second window for every sample tested | Passed |

## 8.4 SYSTEM AND FIELD TESTS (HARDWARE)

System level tests, bench tests of each hardware module, pairwise
integration tests, full cycle tests on USB and then on battery power, flow
calibration, spray volume checks, end to end cycle timing over at least ten
runs, and a field trial comparing constant rate and variable rate chemical
use, are specified in `Capstone/hardware_evidence/HARDWARE_TEST_DATA.md` and
described step by step in Chapter 5 (section 5.8). Three of these tests
have now been run on the real ESP32-CAM and Arduino Nano and are reported
in full, with their real Serial Monitor output, in Chapter 5, section
5.8.2: a standalone bench test of the Nano's relay and solenoid valve
(dry, all four categories, relay click and valve open and close confirmed
for categories 1 to 3, correct no action on category 0); a standalone
bench test of the ESP32-CAM's camera, WiFi connection and one Flask API
call; and one automated pairwise integration cycle of the fully assembled
system, camera to WiFi to Flask server to severity measurement to a serial
command received by the Nano, carrying the honest caveat (also repeated in
Chapter 5, section 5.8.2 and Chapter 9) that this particular cycle fired
on a GPIO13 boot condition rather than a deliberately timed button press,
even though the capture, classification and command themselves are real.
The flow calibration, the spray volume check with water, the full battery
powered run, the end to end cycle timing table and the field trial remain
NOT DONE in Table 5.4, because the pump, tubing and battery pack have not
yet been assembled with the solenoid valve (Chapter 5, section 5.11), and
no photographs or screenshots had been added to the `hardware_evidence/`
folder. This is expected at this stage of the project and is not treated
as a software defect; these remaining tests become runnable once the
liquid path and power system are assembled.

## 8.5 TEST CASE SUMMARY

{{TABLE:test_case_summary|Overall test case summary.}}
| Test level | Cases | Passed | Failed | Source |
|---|---|---|---|---|
| Unit tests (severity and dosing logic) | 37 | 37 | 0 | report/content/unit_test_results.json |
| API integration tests | 13 | 13 | 0 | report/content/api_test_results.json |
| Pipeline simulation (real images, end to end) | 49 images | see Chapter 9 for accuracy figures | n/a | report/content/pipeline_results.json |
| Hardware bench tests (Nano relay/valve, ESP32-CAM camera/WiFi/API) | 2 | 2 | 0 | Capstone/hardware_evidence/HARDWARE_TEST_DATA.md section B, Chapter 5 section 5.8.2 |
| Hardware pairwise integration (one automated cycle, caveat noted) | 1 | 1 | 0 | Capstone/hardware_evidence/HARDWARE_TEST_DATA.md section C, Chapter 5 section 5.8.2 |
| Hardware flow calibration, wet spray check, full field trial | pending | pending | pending | Capstone/hardware_evidence/HARDWARE_TEST_DATA.md sections D, E, F, G, H |

All software level tests (unit and API) that were run, passed completely.
The pipeline simulation in Chapter 9 is reported separately because it
measures end to end behaviour on a small, hand picked sample rather than
pass or fail test cases, and its accuracy numbers are lower than the held
out validation accuracy for reasons explained there; it should not be read
as a failing test, but as an honest, labelled software simulation.
