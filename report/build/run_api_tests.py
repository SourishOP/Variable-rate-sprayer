"""Integration tests of the real Flask service (app/server.py) using its test client.

Records status codes, JSON fields and response times. Output:
report/content/api_test_results.json
"""
import io
import json
import os
import statistics
import sys
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "app"))
import server  # noqa: E402

TEST_DIR = os.path.join(ROOT, "data", "sample_images")
REQUIRED = ["disease_class", "confidence", "severity_percent", "category", "category_code",
            "reduction_coefficient", "base_coefficient", "disease_factor", "low_confidence",
            "leaf_pixels", "diseased_pixels", "seg_method", "spray_time_s", "spray_params",
            "overlay_png", "mode"]
cases = []


def record(case_id, description, expected, actual, passed, extra=None):
    row = {"id": case_id, "description": description, "expected": str(expected),
           "actual": str(actual), "passed": bool(passed)}
    if extra:
        row.update(extra)
    cases.append(row)


server._try_load_model()
client = server.app.test_client()

r = client.get("/health")
j = r.get_json()
record("I1", "GET /health returns status ok and model mode", "200, ok, model", "%d, %s, %s" % (r.status_code, j.get("status"), j.get("mode")),
       r.status_code == 200 and j.get("status") == "ok" and j.get("mode") == "model")
record("I2", "health lists the six classes", 6, len(j.get("classes", [])), len(j.get("classes", [])) == 6)

r = client.get("/")
record("I3", "GET / serves the web page", "200 and html", "%d, %s" % (r.status_code, r.mimetype),
       r.status_code == 200 and r.mimetype == "text/html")

r = client.post("/predict")
record("I4", "POST /predict without an image is rejected", 400, r.status_code, r.status_code == 400)

r = client.post("/predict", data=b"not an image", content_type="application/octet-stream")
record("I5", "POST /predict with bytes that are not an image is rejected", 400, r.status_code, r.status_code == 400)

times = []
picked = []
for folder in ["Bacterial_Blight", "Brown_Spot", "healthy", "leaf_smut", "Neck Blast"]:
    fdir = os.path.join(TEST_DIR, folder)
    files = sorted(f for f in os.listdir(fdir) if f.lower().endswith((".jpg", ".png", ".jpeg")))
    picked.append(os.path.join(fdir, files[0]))
n = 5
for path in picked:
    with open(path, "rb") as fh:
        data = fh.read()
    t0 = time.perf_counter()
    r = client.post("/predict", data={"image": (io.BytesIO(data), os.path.basename(path))},
                    content_type="multipart/form-data")
    dt = (time.perf_counter() - t0) * 1000
    times.append(dt)
    j = r.get_json() or {}
    missing = [k for k in REQUIRED if k not in j]
    n += 1
    record("I%d" % n, "multipart upload of %s returns all response fields" % os.path.relpath(path, TEST_DIR).replace("\\", "/"),
           "200 and no missing fields", "%d, missing=%s, %.0f ms" % (r.status_code, missing, dt),
           r.status_code == 200 and not missing, {"ms": round(dt, 1)})

with open(picked[1], "rb") as fh:
    data = fh.read()
r = client.post("/predict", data=data, content_type="application/octet-stream")
j = r.get_json() or {}
n += 1
record("I%d" % n, "raw image bytes in the request body are accepted (the form the ESP32-CAM sends)", 200, r.status_code,
       r.status_code == 200 and "spray_time_s" in j)

r = client.post("/predict?A=400&d=20&Qs=4.0", data=data, content_type="application/octet-stream")
j2 = r.get_json() or {}
sp = j2.get("spray_params", {})
n += 1
expected_a = round(j2.get("reduction_coefficient", 0) * 400 / (20 * 10), 4)
record("I%d" % n, "query values A=400, d=20, Qs=4.0 change the per-hill dose a = C x A / (d x 10)", expected_a,
       sp.get("a_ml_per_hill"), abs(float(sp.get("a_ml_per_hill", -1)) - expected_a) < 1e-4)

# response values stay inside the valve window
ok_window = True
for path in picked:
    with open(path, "rb") as fh:
        j = client.post("/predict", data=fh.read(), content_type="application/octet-stream").get_json()
    ts = j["spray_time_s"]
    ok_window = ok_window and (ts == 0 or 0.5 <= ts <= 3.0)
n += 1
record("I%d" % n, "spray_time_s is 0 or inside the 0.5 to 3.0 s window for every sample", True, ok_window, ok_window)

passed = sum(1 for c in cases if c["passed"])
out = {"total": len(cases), "passed": passed, "failed": len(cases) - passed,
       "median_ms": round(statistics.median(times), 1), "max_ms": round(max(times), 1),
       "min_ms": round(min(times), 1), "cases": cases}
path = os.path.join(ROOT, "report", "content", "api_test_results.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("api checks: %d passed %d failed %d | request time ms: median %.0f max %.0f" % (out["total"], passed, out["failed"], out["median_ms"], out["max_ms"]))
for c in cases:
    if not c["passed"]:
        print("FAILED", c["id"], c["description"], "expected", c["expected"], "actual", c["actual"])
