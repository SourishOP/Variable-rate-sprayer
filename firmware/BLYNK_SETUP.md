# Blynk dashboard setup (PaddyGuard Sprayer)

This file is the exact, ready-to-use configuration for the Blynk dashboard
referred to in Chapter 5, section 5.7 of the final report, and matches the
virtual pins already wired into `esp32cam_sprayer.ino`. Blynk needs its own
account per user (it is tied to an email address), so this one step cannot
be done on your behalf; everything else below is filled in and ready.

## Why there is no link in the report yet

A Blynk dashboard link only means something once a real device is pushing
real readings to it. No ESP32-CAM has been flashed or wired yet (see
`HARDWARE_TEST_DATA.md`), so there is nothing truthful to host at a public
URL today. Creating a dashboard and posting a link to it with invented
numbers would misrepresent the system in the same way a fabricated test
result would. The steps below get you a real, live link in about 10
minutes once you have 5 minutes with a web browser; `push_to_blynk.py`
(same folder) can feed it real numbers from the project's own measured
software simulation in the meantime, clearly labelled as such, or from the
real firmware once hardware exists.

## 1. Create the account and device (one time, about 5 minutes)

1. Go to https://blynk.cloud and sign up with a free account (the Blynk
   IoT free "Dev" plan is enough for one device).
2. Create a new Template: name it `PaddyGuard Sprayer`. Blynk will assign
   a Template ID (starts `TMPL...`); copy it into `BLYNK_TEMPLATE_ID` in
   `esp32cam_sprayer.ino`.
3. Inside the template, open the **Datastreams** tab and create exactly
   these five, matching the virtual pins already used in the firmware:

   | Datastream name | Virtual Pin | Data type | Min | Max | Units |
   |---|---|---|---|---|---|
   | Severity | V0 | Double | 0 | 100 | % |
   | Category | V1 | String | - | - | - |
   | Chemical per cycle | V2 | Double | 0 | 10 | mL |
   | Alert | V3 | String | - | - | - |
   | Remote trigger | V4 | Integer | 0 | 1 | - |

4. Open the **Web Dashboard** (or Mobile Dashboard) tab and add five
   widgets, bound to the datastreams above:
   - a **Gauge** on V0 (Severity, 0 to 100)
   - a **Labeled Value** on V1 (Category)
   - a **Chart** (history graph) on V2 (Chemical per cycle), so chemical
     usage over time is visible, matching the brief's "log of chemical
     usage over time"
   - a second **Labeled Value** on V3 (Alert), which simply displays
     whatever text the firmware writes to it, only when severity exceeds
     20 percent (High). (There is no drag and drop "Notification" widget
     in current Blynk IoT bound directly to a datastream the way a Gauge
     is; a Labeled Value is the simplest way to surface this text on the
     dashboard. A real push/email/SMS alert is possible but needs a
     separate Events and Automations setup, see the optional note below.)
   - a **Button** on V4 (Remote trigger), set to "push" mode, so a press
     sets V4 to 1 and the ESP32-CAM's `BLYNK_WRITE(VPIN_REMOTE_TRIGGER)`
     handler (already in `esp32cam_sprayer.ino`) starts a cycle remotely

   Optional, real push notification on V3 instead of (or in addition to)
   the Labeled Value: open the template's **Events** tab, create an Event
   (e.g. "High Severity Alert") linked to the V3 datastream, then on the
   device go to **Actions > Notification Settings**, select that event,
   turn on the Push channel, and pick yourself as the recipient.
5. Go to the **Device Info** tab of your device (created automatically
   from the template) and copy its **Auth Token**. Paste it into
   `BLYNK_AUTH_TOKEN` in `esp32cam_sprayer.ino`, and set
   `#define BLYNK_ENABLED 1` (it is `0` by default so the sketch compiles
   and runs the spray logic even before this step is done).
6. Your dashboard's shareable link appears under **Web Dashboard > Share**
   as `https://blynk.cloud/dashboard/<your-dashboard-id>`. That is the
   real, live link to put in the report once step 7 below has pushed at
   least one reading to it.

## 2. Feed it real data

Once the account and datastreams exist, two different sources can feed
them, and the report must say honestly which one is active:

- **Real hardware** (once the ESP32-CAM and Nano are built and flashed,
  Chapter 5, section 5.8): the firmware itself calls `Blynk.virtualWrite()`
  every cycle. This is genuine field telemetry.
- **The project's own measured software simulation** (available right
  now, no hardware needed): `push_to_blynk.py` in this folder replays the
  49 real pipeline results already reported in Chapter 9
  (`report/content/pipeline_results.json`, the same run the report's
  Table 9.4 and Table 9.5 are built from) to the same datastreams, one
  reading every few seconds, through Blynk's public HTTP API. This lets
  the dashboard widgets be demonstrated live using numbers that are real
  (measured by the project's own code on the project's own test images),
  while being clearly a replay of a software simulation, not a field
  reading. Do not present this as hardware telemetry in the report; call
  it exactly what it is, as section 5.7 of Chapter 5 now does.

## 3. Run the replay

```powershell
$env:BLYNK_AUTH_TOKEN = "paste-your-device-auth-token-here"
python push_to_blynk.py
```

The script prints the dashboard's data as it sends each reading, and
prints the public dashboard URL again at the end as a reminder of where
to look.
