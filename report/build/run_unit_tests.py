"""Unit tests for the real severity and dosing module (model/severity.py).

Each check compares an expected value with the value the module really returns.
Results are written to report/content/unit_test_results.json.
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "model"))
import numpy as np  # noqa: E402
import severity as sev  # noqa: E402

CASES = []


def check(case_id, group, description, expected, actual, tol=None):
    if tol is not None and isinstance(expected, (int, float)):
        ok = abs(float(actual) - float(expected)) <= tol
    else:
        ok = expected == actual
    CASES.append({"id": case_id, "group": group, "description": description,
                  "expected": str(expected), "actual": str(actual), "passed": bool(ok)})


# --- U1 category boundaries ---------------------------------------------------
n = 0
for s, name, c in [(0.0, "Healthy", 0.00), (0.1, "Low", 0.30), (5.0, "Low", 0.30),
                   (5.1, "Medium", 0.55), (20.0, "Medium", 0.55), (20.1, "High", 0.80),
                   (100.0, "High", 0.80)]:
    n += 1
    code, cname, coeff = sev.severity_to_category(s)
    check("U1.%d" % n, "Category mapping", "severity %.1f%% maps to %s with base coefficient %.2f" % (s, name, c),
          "%s/%.2f" % (name, c), "%s/%.2f" % (cname, coeff))

# --- U2 disease factors -------------------------------------------------------
n = 0
for cls, f in [("Bacterial_Blight", 1.20), ("Blast", 1.15), ("Brown_Spot", 1.00), ("Healthy", 0.00),
               ("Leaf_Smut", 0.80), ("Neck_Blast", 1.25), ("Bacterial leaf blight", 1.20),
               ("Healthy Rice Leaf", 0.00), ("Unknown_Disease", 1.00)]:
    n += 1
    check("U2.%d" % n, "Disease factor", "factor for class name '%s'" % cls, f,
          sev.disease_treatment_factor(cls), tol=1e-9)

# --- U3 guards and effective coefficient --------------------------------------
names = ["Bacterial_Blight", "Blast", "Brown_Spot", "Healthy", "Leaf_Smut", "Neck_Blast"]


def probs_for(cls, p):
    arr = [(1 - p) / (len(names) - 1)] * len(names)
    arr[names.index(cls)] = p
    return arr


pred = sev.build_prediction_from_severity(names, probs_for("Brown_Spot", 0.9), 1.0)
check("U3.1", "Guards", "severity 1.0% (below 1.5% floor) is treated as Healthy with no spray",
      "Healthy/0.0", "%s/%.1f" % (pred.disease_class, pred.reduction_coefficient))
pred = sev.build_prediction_from_severity(names, probs_for("Brown_Spot", 0.9), 1.5)
check("U3.2", "Guards", "severity exactly 1.5% is kept as a disease (Low category)",
      "Brown_Spot/Low", "%s/%s" % (pred.disease_class, pred.category))
pred = sev.build_prediction_from_severity(names, probs_for("Leaf_Smut", 0.6), 10.0)
check("U3.3", "Guards", "confidence 0.60 is flagged as low confidence", True, pred.low_confidence)
pred = sev.build_prediction_from_severity(names, probs_for("Leaf_Smut", 0.8), 10.0)
check("U3.4", "Guards", "confidence 0.80 is not flagged", False, pred.low_confidence)
pred = sev.build_prediction_from_severity(names, probs_for("Neck_Blast", 0.95), 40.0)
check("U3.5", "Effective coefficient", "High severity x neck blast factor is clamped to 1.00",
      1.0, pred.reduction_coefficient, tol=1e-9)
pred = sev.build_prediction_from_severity(names, probs_for("Bacterial_Blight", 0.95), 40.0)
check("U3.6", "Effective coefficient", "High severity x bacterial blight (0.80 x 1.20) gives 0.96",
      0.96, pred.reduction_coefficient, tol=1e-9)
pred = sev.build_prediction_from_severity(names, probs_for("Leaf_Smut", 0.95), 3.0)
check("U3.7", "Effective coefficient", "Low severity x leaf smut (0.30 x 0.80) gives 0.24",
      0.24, pred.reduction_coefficient, tol=1e-9)
pred = sev.build_prediction_from_severity(names, probs_for("Healthy", 0.95), 0.0)
check("U3.8", "Effective coefficient", "Healthy leaf gives coefficient 0.00 and category code 0",
      "0.0/0", "%.1f/%d" % (pred.reduction_coefficient, pred.category_code))

# --- U4 spray time ------------------------------------------------------------
n = 0
for c, t in [(0.0, 0.0), (0.30, 1.25), (0.55, 1.875), (0.80, 2.5), (1.0, 3.0), (1.5, 3.0), (-0.2, 0.0)]:
    n += 1
    check("U4.%d" % n, "Spray time", "spray_time(C=%.2f) in seconds" % c, t, sev.spray_time(c), tol=1e-9)
seq = [sev.spray_time(c / 100.0) for c in range(0, 101, 5)]
check("U4.8", "Spray time", "spray time never decreases when the coefficient increases", True,
      all(b >= a for a, b in zip(seq, seq[1:])))
check("U4.9", "Spray time", "every non-zero spray time stays inside the 0.5 to 3.0 s window", True,
      all(t == 0 or 0.5 <= t <= 3.0 for t in seq))

# --- U5 segmentation on a synthetic leaf --------------------------------------
import cv2  # noqa: E402

img = np.full((300, 300, 3), 235, dtype=np.uint8)               # light grey background
cv2.ellipse(img, (150, 150), (110, 70), 0, 0, 360, (40, 160, 50), -1)  # green leaf (BGR)
patch_mask = np.zeros((300, 300), np.uint8)
cv2.rectangle(patch_mask, (130, 130), (190, 170), 255, -1)
img[patch_mask > 0] = (30, 70, 120)                              # brown patch (BGR)
leaf = sev.segment_leaf_mask(img)
lesion = sev.segment_disease_mask(img, leaf)
leaf_area = int(leaf.sum())
expected_pct = 100.0 * int((patch_mask > 0).sum()) / int(leaf_area)
measured_pct = 100.0 * int(lesion.sum()) / max(1, leaf_area)
check("U5.1", "Segmentation (colour method)", "leaf mask area is close to the drawn ellipse (pixels)",
      int(math.pi * 110 * 70), leaf_area, tol=0.05 * math.pi * 110 * 70)
check("U5.2", "Segmentation (colour method)", "measured severity matches the drawn brown patch (% of leaf)",
      round(expected_pct, 2), round(measured_pct, 2), tol=2.0)
clean = img.copy()
clean[patch_mask > 0] = (40, 160, 50)
leaf2 = sev.segment_leaf_mask(clean)
les2 = sev.segment_disease_mask(clean, leaf2)
check("U5.3", "Segmentation (colour method)", "a plain green leaf gives about 0% severity",
      0.0, round(100.0 * int(les2.sum()) / max(1, int(leaf2.sum())), 2), tol=1.0)

# --- U6 output fields ---------------------------------------------------------
d = sev.build_prediction_from_severity(names, probs_for("Blast", 0.9), 12.0).to_dict()
need = {"disease_class", "confidence", "severity_percent", "category", "category_code",
        "reduction_coefficient", "base_coefficient", "disease_factor", "low_confidence", "note"}
check("U6.1", "Output fields", "prediction dictionary carries all ten fields used by the API",
      sorted(need), sorted(set(d.keys()) & need))

passed = sum(1 for c in CASES if c["passed"])
out = {"total": len(CASES), "passed": passed, "failed": len(CASES) - passed, "cases": CASES}
path = os.path.join(ROOT, "report", "content", "unit_test_results.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("unit checks: %d, passed: %d, failed: %d" % (out["total"], passed, out["failed"]))
for c in CASES:
    if not c["passed"]:
        print("FAILED", c["id"], c["description"], "expected", c["expected"], "actual", c["actual"])
