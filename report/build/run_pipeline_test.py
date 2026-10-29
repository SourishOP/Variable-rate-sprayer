"""Run the real PaddyGuard pipeline (classifier + segmentation + dosing) on the
sample images in data/sample_images and record the results.

Outputs:
  report/content/pipeline_results.json   (per image + summary)
  report/figures/overlays/*.png          (mask overlays, small)

Run with the ML virtual environment:
  %LOCALAPPDATA%/final_report_work/venv_ml/Scripts/python.exe run_pipeline_test.py
"""
import json
import os
import statistics
import sys
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(ROOT, "model")
TEST_DIR = os.path.join(ROOT, "data", "sample_images")
OUT_JSON = os.path.join(ROOT, "report", "content", "pipeline_results.json")
OUT_OVL = os.path.join(ROOT, "report", "figures", "overlays")
sys.path.insert(0, MODEL_DIR)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import tensorflow as tf  # noqa: E402
import severity as sev  # noqa: E402

A_LPH, D_HILLS, QS_MLS = 500.0, 25.0, 3.5

FOLDER_TO_CLASS = {
    "Bacterial_Blight": "Bacterial_Blight",
    "Brown_Spot": "Brown_Spot",
    "healthy": "Healthy",
    "leaf_smut": "Leaf_Smut",
    "Neck Blast": "Neck_Blast",
}


def main():
    os.makedirs(OUT_OVL, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "class_names.txt")) as f:
        class_names = [ln.strip() for ln in f if ln.strip()]
    model = tf.keras.models.load_model(os.path.join(MODEL_DIR, "rice_disease_effnetv2b0.keras"))
    from tensorflow.keras.applications.efficientnet_v2 import preprocess_input

    def classify(pil):
        arr = np.asarray(pil.resize((224, 224)), dtype="float32")
        arr = preprocess_input(arr)
        return model.predict(np.expand_dims(arr, 0), verbose=0)[0]

    # warm-up so the first timing is not dominated by graph building
    warm = Image.new("RGB", (300, 300), (40, 160, 60))
    classify(warm)
    sev.measure_severity(warm)

    rows = []
    for folder in sorted(os.listdir(TEST_DIR)):
        fdir = os.path.join(TEST_DIR, folder)
        if not os.path.isdir(fdir):
            continue
        true_class = FOLDER_TO_CLASS.get(folder, folder)
        for name in sorted(os.listdir(fdir)):
            if not name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            pil = Image.open(os.path.join(fdir, name)).convert("RGB")
            t0 = time.perf_counter()
            probs = classify(pil)
            t1 = time.perf_counter()
            sres = sev.measure_severity(pil)
            t2 = time.perf_counter()
            pred = sev.build_prediction_from_severity(class_names, probs, sres.severity_percent)
            ceff = pred.reduction_coefficient
            ts = sev.spray_time(ceff, A_LPH, D_HILLS, QS_MLS)
            a_ml = ceff * A_LPH / (D_HILLS * 10.0)
            overlay = sev.make_overlay(pil)
            ovl_name = "%s__%s.png" % (folder.replace(" ", "_"), os.path.splitext(name)[0])
            ov = Image.fromarray(overlay)
            ov.thumbnail((420, 420))
            ov.save(os.path.join(OUT_OVL, ovl_name))
            raw_top = class_names[int(np.argmax(probs))]
            rows.append({
                "file": "%s/%s" % (folder, name),
                "true_class": true_class,
                "raw_top_class": raw_top,
                "pred_class": pred.disease_class,
                "confidence": round(float(max(probs)), 4),
                "severity_percent": round(sres.severity_percent, 2),
                "leaf_pixels": sres.leaf_pixels,
                "diseased_pixels": sres.diseased_pixels,
                "seg_method": sres.method,
                "category": pred.category,
                "category_code": pred.category_code,
                "base_coefficient": pred.base_coefficient,
                "disease_factor": pred.disease_factor,
                "c_eff": round(ceff, 4),
                "ts_s": round(ts, 3),
                "a_ml_per_hill": round(a_ml, 4),
                "volume_ml": round(ts * QS_MLS, 3),
                "low_confidence": bool(pred.low_confidence),
                "note": pred.note,
                "t_classify_ms": round((t1 - t0) * 1000, 1),
                "t_severity_ms": round((t2 - t1) * 1000, 1),
                "overlay": ovl_name,
            })
            print(rows[-1]["file"], rows[-1]["pred_class"], rows[-1]["severity_percent"], rows[-1]["c_eff"])

    n = len(rows)
    correct_raw = sum(1 for r in rows if r["raw_top_class"] == r["true_class"])
    correct_final = sum(1 for r in rows if r["pred_class"] == r["true_class"])
    per_class = {}
    for r in rows:
        c = per_class.setdefault(r["true_class"], {"n": 0, "correct_raw": 0, "correct_final": 0,
                                                    "sev": [], "ceff": [], "ts": []})
        c["n"] += 1
        c["correct_raw"] += int(r["raw_top_class"] == r["true_class"])
        c["correct_final"] += int(r["pred_class"] == r["true_class"])
        c["sev"].append(r["severity_percent"])
        c["ceff"].append(r["c_eff"])
        c["ts"].append(r["ts_s"])
    per_class_out = {}
    for k, c in per_class.items():
        per_class_out[k] = {
            "n": c["n"], "correct_raw": c["correct_raw"], "correct_final": c["correct_final"],
            "mean_severity": round(statistics.mean(c["sev"]), 2),
            "mean_c_eff": round(statistics.mean(c["ceff"]), 4),
            "mean_ts_s": round(statistics.mean(c["ts"]), 3),
        }
    sum_a = sum(r["a_ml_per_hill"] for r in rows)
    ref_a = n * 1.0 * A_LPH / (D_HILLS * 10.0)
    sum_v = sum(r["volume_ml"] for r in rows)
    ref_v = n * (sev.SPRAY_TS_MIN + 1.0 * (sev.SPRAY_TS_MAX - sev.SPRAY_TS_MIN)) * QS_MLS
    summary = {
        "images": n,
        "accuracy_raw_top_class": round(correct_raw / n, 4),
        "accuracy_after_guards": round(correct_final / n, 4),
        "correct_raw": correct_raw,
        "correct_after_guards": correct_final,
        "equation_dose_total_ml": round(sum_a, 3),
        "equation_dose_constant_ml": round(ref_a, 3),
        "equation_saving_percent": round(100 * (1 - sum_a / ref_a), 2),
        "valve_volume_total_ml": round(sum_v, 2),
        "valve_volume_constant_ml": round(ref_v, 2),
        "valve_saving_percent": round(100 * (1 - sum_v / ref_v), 2),
        "mean_c_eff": round(statistics.mean(r["c_eff"] for r in rows), 4),
        "no_spray_images": sum(1 for r in rows if r["c_eff"] <= 0),
        "median_classify_ms": round(statistics.median(r["t_classify_ms"] for r in rows), 1),
        "median_severity_ms": round(statistics.median(r["t_severity_ms"] for r in rows), 1),
        "max_classify_ms": max(r["t_classify_ms"] for r in rows),
        "max_severity_ms": max(r["t_severity_ms"] for r in rows),
        "design": {"A_lph": A_LPH, "d_hills_per_m2": D_HILLS, "Qs_mls": QS_MLS,
                   "ts_min": sev.SPRAY_TS_MIN, "ts_max": sev.SPRAY_TS_MAX},
        "tensorflow": tf.__version__,
        "classes": class_names,
        "per_class": per_class_out,
        "segmenter_loaded": sev._SEG_MODEL is not None,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
