"""Replay the project's own measured pipeline simulation into a Blynk Cloud
dashboard, through Blynk's public HTTP API (no SDK install needed).

This is NOT a hardware test. It feeds the Severity / Category / Chemical
per cycle / Alert datastreams described in BLYNK_SETUP.md with the real,
already-reported numbers from report/content/pipeline_results.json
(the same 49-image run cited in Chapter 9 of the report), one row every
few seconds, so the dashboard widgets can be demonstrated live before the
physical hardware exists. Once the ESP32-CAM firmware is flashed and
wired (Chapter 5, section 5.8), it pushes to the same datastreams directly
from real field readings instead, and this script is no longer needed.

Requires only the standard library. Set BLYNK_AUTH_TOKEN (see
BLYNK_SETUP.md step 1.5) before running:

    $env:BLYNK_AUTH_TOKEN = "your-device-auth-token"
    python push_to_blynk.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RESULTS_PATH = os.path.join(ROOT, "report", "content", "pipeline_results.json")

BLYNK_SERVER = "https://blynk.cloud/external/api/update"
SEND_INTERVAL_S = 4.0


def blynk_update(token, pin, value):
    """Set one datastream via Blynk's HTTP API. Returns True on success."""
    params = urllib.parse.urlencode({"token": token, pin: value})
    url = f"{BLYNK_SERVER}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:  # noqa: BLE001
        print(f"[blynk] update failed for {pin}={value}: {e}")
        return False


def main():
    token = os.environ.get("BLYNK_AUTH_TOKEN", "").strip()
    if not token:
        print("Set BLYNK_AUTH_TOKEN first. See BLYNK_SETUP.md step 1.5 for")
        print("where to copy it from in the Blynk console.")
        sys.exit(1)

    if not os.path.exists(RESULTS_PATH):
        print(f"Could not find {RESULTS_PATH}.")
        print("Run report/build/run_pipeline_test.py first, or check the path.")
        sys.exit(1)

    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows", [])
    if not rows:
        print("pipeline_results.json has no rows to replay.")
        sys.exit(1)

    print(f"[replay] {len(rows)} real pipeline-simulation readings found in")
    print(f"         {RESULTS_PATH}")
    print("[replay] sending to Blynk every "
          f"{SEND_INTERVAL_S:.0f}s (Ctrl+C to stop early)")
    print("[replay] this is the project's own measured software simulation,")
    print("         NOT live hardware telemetry - label it as such on the dashboard")

    for i, row in enumerate(rows, start=1):
        severity = row.get("severity_percent", 0.0)
        category = row.get("category", "Healthy")
        volume_ml = row.get("volume_ml", 0.0)

        ok_v0 = blynk_update(token, "V0", severity)
        ok_v1 = blynk_update(token, "V1", category)
        ok_v2 = blynk_update(token, "V2", volume_ml)
        ok_v3 = True
        if severity > 20.0:
            ok_v3 = blynk_update(
                token, "V3",
                f"High severity detected ({row.get('file', '?')}), full dose sprayed")

        status = "ok" if (ok_v0 and ok_v1 and ok_v2 and ok_v3) else "one or more updates failed"
        print(f"[{i}/{len(rows)}] {row.get('file', '?'):35s} "
              f"severity={severity:6.2f}%  category={category:8s} "
              f"volume={volume_ml:6.2f}mL  ({status})")

        time.sleep(SEND_INTERVAL_S)

    print("[replay] done. View the dashboard at the Web Dashboard > Share link")
    print("         from BLYNK_SETUP.md step 1.6.")


if __name__ == "__main__":
    main()
