# hardware: build plan and test log

| File | Contents |
|------|----------|
| `hardware_implementation_plan.md` | Architecture, severity mapping and spray equations, bill of materials, pin-by-pin wiring, build phases, safety notes, troubleshooting |
| `HARDWARE_TEST_DATA.md` | Recorded bench and integration tests, with `NOT DONE` where a test was not performed |

## Status

Done: ESP32-CAM and Arduino Nano flashed and bench tested on USB power, ESP32-CAM
to Flask API round trip, ESP32-CAM to Nano serial command, and a dry relay and
valve test.

Not done: pump and water flow test, measured flow rate Qs, battery powered run,
buck converter trim, Blynk from the physical prototype. The test log is the
source of truth and the main README repeats these limits.

The firmware is in [../firmware](../firmware/README.md). Back to the
[main README](../README.md).