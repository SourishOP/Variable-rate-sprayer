"""
Flask backend for the Rice Leaf Disease + Severity demo UI.

Serves the static frontend (app/static/index.html) and a /predict endpoint.

Endpoints:
    GET  /            -> the demo web UI
    GET  /health      -> {"status": "ok", "model_loaded": bool, "mode": ...}
    POST /predict     -> multipart "image" OR raw body bytes; returns JSON:
        {
          "disease_class", "confidence", "severity_percent",
          "leaf_pixels", "diseased_pixels",
          "category", "category_code", "reduction_coefficient",
          "spray_time_s", "spray_params": {A, d, Qs, a_ml_per_hill},
          "overlay_png": "<base64>",       # mask overlay image
          "mode": "model" | "demo"
        }

MODES
    - "model": a trained EfficientNetV2 model is found and used for the disease
      class. Severity is always measured by segmentation (severity.py).
    - "demo":  no model file present. The disease class is inferred by a simple
      heuristic so the whole UI (mask + formulas + animation) is fully
      demonstrable before training finishes. Severity is still real (measured).

Run locally:
    python app/server.py
    # then open http://127.0.0.1:5000

Colab: see app/launch_colab.py for a public share URL.
"""

import io
import os
import sys

from flask import Flask, jsonify, request, send_from_directory

# Make the shared severity module importable regardless of CWD.
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "..", "model")
sys.path.append(MODEL_DIR)

import severity as sev  # noqa: E402

IMG_SIZE = 224
STATIC_DIR = os.path.join(HERE, "static")

MODEL_PATH = os.environ.get(
    "MODEL_PATH", os.path.join(MODEL_DIR, "rice_disease_effnetv2b0.keras")
)
CLASS_NAMES_PATH = os.environ.get(
    "CLASS_NAMES_PATH", os.path.join(MODEL_DIR, "class_names.txt")
)

# Spray equation defaults (from the base paper). Overridable via query/env.
DEFAULT_APP_RATE_LPH = float(os.environ.get("APP_RATE_LPH", "500"))   # A (L/ha)
DEFAULT_HILL_DENSITY = float(os.environ.get("HILL_DENSITY", "25"))    # d (hills/m^2)
DEFAULT_FLOW_RATE_MLS = float(os.environ.get("FLOW_RATE_MLS", "3.5"))  # Qs (mL/s)

try:
    from flask_cors import CORS
    _HAS_CORS = True
except ImportError:
    _HAS_CORS = False

app = Flask(__name__, static_folder=None)
if _HAS_CORS:
    CORS(app)

_model = None
_class_names = None
_mode = None  # "model" or "demo"


def _load_class_names():
    if os.path.exists(CLASS_NAMES_PATH):
        with open(CLASS_NAMES_PATH) as f:
            names = [ln.strip() for ln in f if ln.strip()]
        if names:
            return names
    return list(sev.DEFAULT_CLASS_NAMES)


def _try_load_model():
    """Attempt to load a trained model. Set mode to 'model' or 'demo'."""
    global _model, _class_names, _mode
    _class_names = _load_class_names()
    if os.path.exists(MODEL_PATH):
        try:
            import tensorflow as tf
            _model = tf.keras.models.load_model(MODEL_PATH)
            _mode = "model"
            print(f"[server] loaded model: {MODEL_PATH}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"[server] model present but failed to load ({e}); demo mode.")
    else:
        print("[server] no model file found; running in DEMO mode "
              "(severity is still measured by segmentation).")
    _mode = "demo"


def _pil_from_bytes(image_bytes):
    from PIL import Image
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _pil_from_rgb565(raw, width, height):
    """Build an RGB image from a raw big-endian RGB565 frame.

    The ESP32-CAM clone sensor used in this project has no hardware JPEG and
    the on-device software JPEG encoder exhausts the ESP32's internal RAM, so
    the firmware ships the raw RGB565 frame instead. Each pixel is 2 bytes,
    big-endian (the esp32-camera default): RRRRRGGG GGGBBBBB. We expand to 8
    bits per channel and let PIL take over from there.
    """
    import numpy as np
    from PIL import Image

    expected = width * height * 2
    if len(raw) < expected:
        raise ValueError(
            f"RGB565 body too short: got {len(raw)} bytes, "
            f"need {expected} for {width}x{height}"
        )
    px = np.frombuffer(raw[:expected], dtype=">u2").astype(np.uint32)
    r = ((px >> 11) & 0x1F) << 3
    g = ((px >> 5) & 0x3F) << 2
    b = (px & 0x1F) << 3
    rgb = np.stack([r, g, b], axis=-1).astype(np.uint8).reshape((height, width, 3))
    return Image.fromarray(rgb, mode="RGB")


def _classify_with_model(pil):
    import numpy as np
    from tensorflow.keras.applications.efficientnet_v2 import preprocess_input

    img = pil.resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img, dtype="float32")
    arr = preprocess_input(arr)
    batch = np.expand_dims(arr, axis=0)
    probs = _model.predict(batch, verbose=0)[0]
    return probs


def _classify_demo(pil, severity_percent):
    """Heuristic pseudo-classification for demo mode.

    Returns a probabilities vector aligned with _class_names. If the leaf is
    essentially clean, favor Healthy; otherwise favor the first non-healthy
    class. This is ONLY to make the UI complete without a trained model; the
    severity number itself is real (measured by segmentation).
    """
    n = len(_class_names)
    probs = [0.0] * n
    healthy_idx = next(
        (i for i, c in enumerate(_class_names) if c.lower() == "healthy"), None
    )
    if severity_percent <= 0.5 and healthy_idx is not None:
        probs[healthy_idx] = 0.98
        for i in range(n):
            if i != healthy_idx:
                probs[i] = 0.02 / max(1, n - 1)
    else:
        # pick first non-healthy class as the "detected" disease
        disease_idx = next(
            (i for i in range(n) if i != healthy_idx), 0
        )
        probs[disease_idx] = 0.9
        for i in range(n):
            if i != disease_idx:
                probs[i] = 0.1 / max(1, n - 1)
    return probs


def _extract_image_bytes(req):
    # Multipart upload (web UI) first.
    if req.files and "image" in req.files:
        return req.files["image"].read()
    # Raw body (ESP32 posts application/octet-stream). Read it straight from
    # the input stream so it works regardless of content type and is not
    # affected by any earlier access to request.data/form. content_length
    # tells us how much to read.
    try:
        n = req.content_length or 0
        if n > 0:
            raw = req.stream.read(n)
            if raw:
                return raw
    except Exception:  # noqa: BLE001
        pass
    # Fallbacks.
    raw = req.get_data(cache=True, as_text=False)
    if raw:
        return raw
    return None


def _parse_box(req, size):
    """Parse an optional leaf bounding box from the request.

    Accepts a 'box' field/param as "x1,y1,x2,y2". Values may be pixel coords or
    normalized [0,1] (auto-detected: if all <= 1, scale by image size).
    Returns (x1, y1, x2, y2) in pixels, or None.
    """
    raw = None
    if req.form and "box" in req.form:
        raw = req.form["box"]
    elif "box" in req.args:
        raw = req.args["box"]
    if not raw:
        return None
    try:
        parts = [float(v) for v in raw.split(",")]
        if len(parts) != 4:
            return None
        w, h = size
        if all(0.0 <= p <= 1.0 for p in parts):
            x1, y1, x2, y2 = parts[0] * w, parts[1] * h, parts[2] * w, parts[3] * h
        else:
            x1, y1, x2, y2 = parts
        x1, x2 = sorted((max(0, min(w, x1)), max(0, min(w, x2))))
        y1, y2 = sorted((max(0, min(h, y1)), max(0, min(h, y2))))
        if x2 - x1 < 5 or y2 - y1 < 5:
            return None
        return (x1, y1, x2, y2)
    except Exception:  # noqa: BLE001
        return None


def _parse_polygon(req, size):
    """Parse an optional free-form leaf polygon from the request.

    Accepts a 'polygon' field/param as flat "x1,y1,x2,y2,...,xn,yn". Values may
    be pixel coords or normalized [0,1] (auto-detected). Returns a list of
    (x, y) pixel tuples (>= 3 points), or None.
    """
    raw = None
    if req.form and "polygon" in req.form:
        raw = req.form["polygon"]
    elif "polygon" in req.args:
        raw = req.args["polygon"]
    if not raw:
        return None
    try:
        nums = [float(v) for v in raw.split(",") if v.strip() != ""]
        if len(nums) < 6 or len(nums) % 2 != 0:
            return None
        w, h = size
        normalized = all(0.0 <= v <= 1.0 for v in nums)
        pts = []
        for i in range(0, len(nums), 2):
            x, y = nums[i], nums[i + 1]
            if normalized:
                x, y = x * w, y * h
            x = max(0, min(w, x))
            y = max(0, min(h, y))
            pts.append((x, y))
        return pts if len(pts) >= 3 else None
    except Exception:  # noqa: BLE001
        return None


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/health")
def health():
    if _mode is None:
        _try_load_model()
    return jsonify({
        "status": "ok",
        "model_loaded": _model is not None,
        "mode": _mode,
        "classes": _class_names,
    })


@app.route("/predict", methods=["POST"])
def predict():
    if _mode is None:
        _try_load_model()

    fmt = (request.args.get("fmt")
           or request.headers.get("X-Image-Format")
           or "").lower()

    def _diag(msg):
        line = f"{msg}\n"
        try:
            with open(os.path.join(HERE, "predict_debug.log"), "a") as _f:
                _f.write(line)
        except Exception:  # noqa: BLE001
            pass
        print(line, end="", flush=True)

    # Read the body BEFORE touching request.data/form, so the input stream is
    # not consumed out from under us.
    image_bytes = _extract_image_bytes(request)

    _diag(f"[predict] from={request.remote_addr} fmt={fmt!r} "
          f"args={dict(request.args)} content_length={request.content_length} "
          f"extracted={len(image_bytes) if image_bytes else 0}")

    if not image_bytes:
        _diag("[predict] 400: no image bytes extracted")
        return jsonify({"error": "no image provided"}), 400

    # Raw RGB565 path: the ESP32-CAM firmware sends the raw frame (no JPEG)
    # when it declares format=rgb565 with width/height, either as query params
    # (?fmt=rgb565&w=160&h=120) or the X-Image-Format / X-Image-Width /
    # X-Image-Height headers. Everything else is treated as an encoded image
    # (JPEG/PNG) exactly as before.
    try:
        if fmt in ("rgb565", "raw565"):
            w = int(request.args.get("w") or request.headers.get("X-Image-Width"))
            h = int(request.args.get("h") or request.headers.get("X-Image-Height"))
            _diag(f"[predict] rgb565 decode w={w} h={h} bytes={len(image_bytes)}")
            pil = _pil_from_rgb565(image_bytes, w, h)
            # Debug aid: keep the last frame the ESP32 sent so colours / framing
            # can be checked by eye (wrong byte order would swap colours).
            try:
                pil.save(os.path.join(HERE, "last_esp32_frame.png"))
            except Exception as save_err:  # noqa: BLE001
                print(f"[server] could not save debug frame: {save_err}")
        else:
            pil = _pil_from_bytes(image_bytes)
    except Exception as e:  # noqa: BLE001
        _diag(f"[predict] 400: decode failed: {e}")
        return jsonify({"error": f"could not decode image: {e}"}), 400

    # Optional leaf isolation. A free-form 'polygon' (traced outline) takes
    # priority; otherwise a 'box' (with MobileSAM); otherwise auto color mask.
    box = _parse_box(request, pil.size)
    polygon = _parse_polygon(request, pil.size)

    # Measure severity (real, from segmentation) once; reused for the overlay.
    try:
        sres = sev.measure_severity(pil, box=box, polygon=polygon)
        seg_method = getattr(sres, "method", "unknown")
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"severity segmentation failed: {e}"}), 500

    # Classify disease.
    try:
        if _mode == "model":
            probs = _classify_with_model(pil)
        else:
            probs = _classify_demo(pil, sres.severity_percent)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"classification failed: {e}"}), 500

    # Build the prediction using the measured severity (avoids re-segmenting).
    pred = sev.build_prediction_from_severity(
        _class_names, probs, sres.severity_percent
    )

    # Spray-time equation from the base paper.
    app_rate = float(request.args.get("A", DEFAULT_APP_RATE_LPH))
    hill_density = float(request.args.get("d", DEFAULT_HILL_DENSITY))
    flow_rate = float(request.args.get("Qs", DEFAULT_FLOW_RATE_MLS))
    a_ml_per_hill = (pred.reduction_coefficient * app_rate) / (hill_density * 10.0)
    ts = sev.spray_time(pred.reduction_coefficient, app_rate, hill_density, flow_rate)

    # Overlay PNG. The web UI wants it, but the ESP32 does not and cannot hold
    # the large base64 string (its JSON buffer overflows -> NoMemory). Clients
    # can skip it with ?overlay=0 (the firmware does this); it is also skipped
    # automatically for the raw RGB565 path.
    want_overlay = (request.args.get("overlay", "1") != "0") and fmt not in (
        "rgb565", "raw565")
    if want_overlay:
        try:
            overlay_b64 = sev.overlay_png_base64(pil, box=box, polygon=polygon)
        except Exception as e:  # noqa: BLE001
            overlay_b64 = None
            print(f"[server] overlay generation failed: {e}")
    else:
        overlay_b64 = None

    result = pred.to_dict()
    result.update({
        "leaf_pixels": sres.leaf_pixels,
        "diseased_pixels": sres.diseased_pixels,
        "seg_method": seg_method,
        "spray_time_s": round(ts, 3),
        "spray_params": {
            "A_lph": app_rate,
            "d_hills_per_m2": hill_density,
            "Qs_mls": flow_rate,
            "a_ml_per_hill": round(a_ml_per_hill, 4),
            "ts_min": sev.SPRAY_TS_MIN,
            "ts_max": sev.SPRAY_TS_MAX,
        },
        "overlay_png": overlay_b64,
        "mode": _mode,
    })
    return jsonify(result)


if __name__ == "__main__":
    _try_load_model()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
