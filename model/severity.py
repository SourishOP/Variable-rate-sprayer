"""
Rice leaf disease -> severity mapping.

This module provides TWO things:

1. Disease classification post-processing: turn a model's softmax output into a
   predicted disease class + confidence.

2. Segmentation-based SEVERITY measurement (Option B): given the original leaf
   image, segment the leaf from the background and then segment the diseased
   (lesion) pixels using classical computer vision. Severity is the ratio of
   diseased pixels to total leaf pixels, expressed as a percentage.

       severity_percent = 100 * (diseased_pixels / leaf_pixels)

   This is the definition used by the base paper (Tewari et al., 2020) and does
   NOT require pixel-mask training data because it uses color-space thresholding
   (HSV / LAB + Otsu) rather than a learned segmenter.

The class/category mapping and the spray-time equation are preserved so the rest
of the project (docs, server) keeps working.
"""

import os
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

# Default class order (alphabetical, matching Keras directory scanning).
# Adjust if your dataset folders differ. Written to class_names.txt at train time.
DEFAULT_CLASS_NAMES = [
    "Bacterial_Blight",
    "Blast",
    "Brown_Spot",
    "Healthy",
    "Leaf_Smut",
    "Neck_Blast",
]

# Category definitions: (code, name, base reduction coefficient C_base).
#
# NOTE: base coefficients top out at 0.80 (not 1.00) so the disease-specific
# factor (which can be up to ~1.25) always has headroom to change the effective
# dose. C_eff is later clamped to [0, 1], so the worst case (High + aggressive
# disease) reaches the full 1.0 dose, while lighter diseases stay below it.
CATEGORY_HEALTHY = (0, "Healthy", 0.00)
CATEGORY_LOW = (1, "Low", 0.30)
CATEGORY_MEDIUM = (2, "Medium", 0.55)
CATEGORY_HIGH = (3, "High", 0.80)

# ---------------------------------------------------------------------------
# Disease-specific treatment intensity.
#
# Severity (from segmentation) sets the BASE coefficient C_severity. But
# different diseases warrant different treatment intensity for the same visible
# area: e.g. bacterial blight spreads aggressively and is treated more heavily,
# while leaf smut is comparatively minor. So the CNN's disease class now
# genuinely influences the spray dose via a per-disease multiplier.
#
#     C_effective = clamp( C_severity * disease_factor , 0 , 1 )
#
# These factors are configurable defaults; tune them with an agronomist. Keys
# are matched case-insensitively and ignore spaces/underscores, so both
# "Bacterial_Blight" and "Bacterial leaf blight" resolve to the same entry.
# ---------------------------------------------------------------------------
DISEASE_TREATMENT_FACTOR = {
    "bacterialblight": 1.20,       # aggressive, treat more heavily
    "bacterialleafblight": 1.20,
    "blast": 1.15,                 # rice blast spreads fast, treat heavily
    "leafblast": 1.15,
    "neckblast": 1.25,             # neck blast is the most damaging stage
    "brownspot": 1.00,             # baseline
    "leafsmut": 0.80,              # comparatively minor
    "healthy": 0.00,               # never spray a healthy leaf
}
DEFAULT_DISEASE_FACTOR = 1.00      # unknown disease -> neutral

# --- Honesty guards (tunable via env) ---------------------------------------
# 1) Severity floor: if the measured diseased area is below this % of the leaf,
#    treat the leaf as effectively HEALTHY (kills noise from a few stray specks
#    being called a disease). Set to 0 to disable.
MIN_SEVERITY_PERCENT = float(os.environ.get("MIN_SEVERITY_PERCENT", "1.5"))
# 2) Confidence gate: if the classifier's top probability is below this, we mark
#    the result as low-confidence / uncertain rather than asserting a disease.
#    Set to 0.70 because with 6 classes a sub-70% top score is a weak guess
#    (random ~17%); such predictions should be shown as uncertain, not asserted.
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.70"))


def _disease_key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _is_healthy(name: str) -> bool:
    """True if the class name denotes a healthy leaf.

    Robust to dataset naming: matches 'Healthy', 'healthy_leaf', 'Healthy Rice
    Leaf', 'normal', etc.
    """
    k = _disease_key(name)
    return "healthy" in k or k == "normal"


def disease_treatment_factor(disease_class: str) -> float:
    """Return the treatment-intensity multiplier for a disease class name."""
    if _is_healthy(disease_class):
        return 0.0  # never spray a healthy leaf, whatever the folder is named
    return DISEASE_TREATMENT_FACTOR.get(_disease_key(disease_class),
                                        DEFAULT_DISEASE_FACTOR)


@dataclass
class Prediction:
    disease_class: str
    confidence: float          # 0..1 softmax probability of predicted class
    severity_percent: float    # 0..100, MEASURED from segmentation
    category: str
    category_code: int
    reduction_coefficient: float          # EFFECTIVE C used for spraying
    base_coefficient: float = 0.0         # C from severity alone
    disease_factor: float = 1.0           # per-disease multiplier applied
    low_confidence: bool = False          # classifier top prob below MIN_CONFIDENCE
    note: str = ""                        # human-readable caveat, if any

    def to_dict(self) -> dict:
        return {
            "disease_class": self.disease_class,
            "confidence": round(self.confidence, 4),
            "severity_percent": round(self.severity_percent, 2),
            "category": self.category,
            "category_code": self.category_code,
            "reduction_coefficient": self.reduction_coefficient,
            "base_coefficient": round(self.base_coefficient, 4),
            "disease_factor": self.disease_factor,
            "low_confidence": self.low_confidence,
            "note": self.note,
        }


def severity_to_category(severity_percent: float):
    """Map a severity percentage to (code, name, coefficient).

    Thresholds follow the base paper (Tewari et al., 2020) plus a Healthy=0
    category that the paper did not have.

        <= 0%        -> Healthy
        0 - 5%       -> Low
        5 - 20%      -> Medium
        > 20%        -> High
    """
    if severity_percent <= 0.0:
        return CATEGORY_HEALTHY
    if severity_percent <= 5.0:
        return CATEGORY_LOW
    if severity_percent <= 20.0:
        return CATEGORY_MEDIUM
    return CATEGORY_HIGH


# --------------------------------------------------------------------------- #
# Segmentation-based severity (Option B)
# --------------------------------------------------------------------------- #

def _to_bgr_uint8(image) -> np.ndarray:
    """Accept a path, a PIL image, or a numpy array and return BGR uint8.

    Requires OpenCV. We import cv2 lazily so that importing this module for the
    mapping helpers alone does not require OpenCV to be installed.
    """
    import cv2

    if isinstance(image, str):
        bgr = cv2.imread(image, cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(f"Could not read image: {image}")
        return bgr

    arr = np.asarray(image)
    if arr.dtype != np.uint8:
        # assume float in [0,1] or [0,255]
        if arr.max() <= 1.0:
            arr = (arr * 255.0).clip(0, 255)
        arr = arr.astype(np.uint8)

    if arr.ndim == 2:  # grayscale
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if arr.shape[2] == 4:  # RGBA
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    # numpy images from PIL are RGB; convert to BGR for OpenCV consistency
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def segment_leaf_mask(bgr: np.ndarray) -> np.ndarray:
    """Return a boolean mask of the LEAF region (True = leaf, False = background).

    Strategy: leaves (healthy green + diseased brown/yellow) are more saturated
    and less blue than typical neutral/white/gray backgrounds. We threshold in
    HSV on saturation + value, then keep the largest connected component and fill
    holes so lesion areas inside the leaf are not dropped.
    """
    import cv2

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # Otsu on saturation isolates colored (leaf) vs neutral (background) pixels.
    _, sat_mask = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Drop very dark pixels (shadows) and pure-white blowouts.
    value_ok = cv2.inRange(v, 30, 250)
    mask = cv2.bitwise_and(sat_mask, value_ok)

    # Morphological cleanup.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Keep the largest connected component (the leaf).
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = np.where(labels == largest, 255, 0).astype(np.uint8)

    # Fill interior holes (lesions) so the leaf area includes diseased regions.
    filled = mask.copy()
    h, w = mask.shape
    ff_mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(filled, ff_mask, (0, 0), 255)
    holes = cv2.bitwise_not(filled)
    leaf = cv2.bitwise_or(mask, holes)

    return leaf.astype(bool)


def segment_disease_mask(bgr: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Return a boolean mask of DISEASED (lesion) pixels within the leaf.

    Healthy rice tissue is green (hue ~35-85 in OpenCV's 0-179 scale). Diseased
    lesions are brown / yellow / tan / gray, i.e. NOT green. So within the leaf
    mask, any pixel that is not sufficiently green-and-saturated is treated as a
    lesion. We also require the leaf pixel to be reasonably bright to avoid
    counting shadow.

    NOTE: this is the CLASSICAL fallback. When a trained lesion-segmentation
    model is available (lesion_segmenter.keras), segment_lesion_model() is used
    instead for far better results on cluttered field photos.
    """
    import cv2

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]

    # Healthy green: hue band + minimum saturation.
    green = (h >= 35) & (h <= 85) & (s >= 40)

    diseased = leaf_mask & (~green)
    return diseased


# --------------------------------------------------------------------------- #
# Trained lesion segmentation model (Option C) with graceful fallback
# --------------------------------------------------------------------------- #
_SEG_MODEL = None
_SEG_MODEL_TRIED = False
_SEG_IMG_SIZE = 256

# Probability threshold above which a pixel is called "lesion". Higher = more
# strict (tighter masks, less over-detection). Tunable via env for demo tuning.
SEG_THRESHOLD = float(os.environ.get("SEG_THRESHOLD", "0.5"))

# Where the trained segmenter is expected. Overridable via env.
SEG_MODEL_PATH = os.environ.get(
    "SEG_MODEL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "lesion_segmenter.keras"),
)


def _load_seg_model():
    """Load the trained lesion segmenter once. Returns the model or None.

    Never raises: if TensorFlow or the file is missing, returns None so callers
    transparently fall back to the color method.
    """
    global _SEG_MODEL, _SEG_MODEL_TRIED
    if _SEG_MODEL_TRIED:
        return _SEG_MODEL
    _SEG_MODEL_TRIED = True
    if not os.path.exists(SEG_MODEL_PATH):
        return None
    try:
        import tensorflow as tf
        _SEG_MODEL = tf.keras.models.load_model(SEG_MODEL_PATH, compile=False)
        print(f"[severity] loaded lesion segmenter: {SEG_MODEL_PATH}")
    except Exception as e:  # noqa: BLE001
        print(f"[severity] could not load segmenter ({e}); using color method.")
        _SEG_MODEL = None
    return _SEG_MODEL


def segment_lesion_model(bgr: np.ndarray):
    """Predict a boolean lesion mask using the trained model, or None.

    Returns a full-resolution boolean array (True = lesion) matching `bgr`, or
    None when no model is available.
    """
    model = _load_seg_model()
    if model is None:
        return None
    import cv2
    import numpy as _np

    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    inp = cv2.resize(rgb, (_SEG_IMG_SIZE, _SEG_IMG_SIZE), interpolation=cv2.INTER_LINEAR)
    inp = inp.astype("float32")[None, ...]
    pred = model.predict(inp, verbose=0)[0, :, :, 0]
    mask_small = (pred > SEG_THRESHOLD)
    mask = cv2.resize(mask_small.astype(_np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
    return mask.astype(bool)


# --------------------------------------------------------------------------- #
# Interactive leaf isolation via MobileSAM (Option B) with graceful fallback
# --------------------------------------------------------------------------- #
_SAM_MODEL = None
_SAM_TRIED = False

# MobileSAM weights (small, CPU-friendly). ultralytics downloads it on first use.
# Default to the copy stored next to this file so we don't re-download a second
# copy into whatever the working directory happens to be.
SAM_WEIGHTS = os.environ.get(
    "SAM_WEIGHTS",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile_sam.pt"),
)


def _load_sam():
    """Load MobileSAM once via ultralytics. Returns model or None (never raises)."""
    global _SAM_MODEL, _SAM_TRIED
    if _SAM_TRIED:
        return _SAM_MODEL
    _SAM_TRIED = True
    try:
        from ultralytics import SAM
        _SAM_MODEL = SAM(SAM_WEIGHTS)
        print(f"[severity] loaded MobileSAM: {SAM_WEIGHTS}")
    except Exception as e:  # noqa: BLE001
        print(f"[severity] MobileSAM unavailable ({e}); using color leaf mask.")
        _SAM_MODEL = None
    return _SAM_MODEL


def segment_leaf_sam(bgr: np.ndarray, box):
    """Segment the leaf inside a user-drawn box using MobileSAM.

    `box` is (x1, y1, x2, y2) in pixel coordinates of `bgr`. Returns a boolean
    leaf mask, or None if SAM is unavailable / fails.
    """
    model = _load_sam()
    if model is None or box is None:
        return None
    import cv2
    import numpy as _np

    try:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        x1, y1, x2, y2 = [int(v) for v in box]
        results = model(rgb, bboxes=[[x1, y1, x2, y2]], verbose=False)
        r = results[0]
        if r.masks is None or len(r.masks.data) == 0:
            return None
        # Union of returned masks (usually one for a box prompt).
        m = r.masks.data.cpu().numpy()  # (n, H, W)
        mask = (_np.max(m, axis=0) > 0.5)
        h, w = bgr.shape[:2]
        if mask.shape != (h, w):
            mask = cv2.resize(mask.astype(_np.uint8), (w, h),
                              interpolation=cv2.INTER_NEAREST).astype(bool)
        return mask
    except Exception as e:  # noqa: BLE001
        print(f"[severity] SAM segmentation failed ({e}); using color leaf mask.")
        return None


def polygon_to_mask(polygon, height, width) -> np.ndarray:
    """Rasterize a free-form polygon (list of (x, y) pixel points) to a bool mask.

    Returns a boolean array (True inside the traced outline), or None if the
    polygon is degenerate (fewer than 3 points).
    """
    import cv2

    if polygon is None or len(polygon) < 3:
        return None
    pts = np.array([[int(round(x)), int(round(y))] for x, y in polygon], dtype=np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    return mask.astype(bool)


def compute_masks(bgr: np.ndarray, box=None, polygon=None):
    """Return (leaf_mask, lesion_mask, method) as boolean arrays.

    Leaf mask (priority order):
        1. `polygon` - a free-form outline the user traced -> used DIRECTLY as
           the leaf region (most precise, user-defined boundary).
        2. `box` + MobileSAM - SAM segments the leaf inside the box.
        3. Color-based leaf mask (automatic fallback).
    Lesion mask:
        - Trained segmenter when available, else the color method.
    Method string encodes both, e.g. "poly+model", "sam+model", "color+color".
    """
    h, w = bgr.shape[:2]
    # --- leaf ---
    leaf = None
    leaf_src = "color"

    poly_leaf = polygon_to_mask(polygon, h, w) if polygon is not None else None
    if poly_leaf is not None and poly_leaf.sum() > 0:
        leaf = poly_leaf
        leaf_src = "poly"
    else:
        sam_leaf = segment_leaf_sam(bgr, box) if box is not None else None
        if sam_leaf is not None and sam_leaf.sum() > 0:
            leaf = sam_leaf
            leaf_src = "sam"
        else:
            leaf = segment_leaf_mask(bgr)

    # --- lesion ---
    model_lesion = segment_lesion_model(bgr)
    if model_lesion is not None:
        lesion = model_lesion & leaf
        lesion_src = "model"
        if lesion.sum() == 0 and model_lesion.sum() > 0 and leaf_src == "color":
            # Only widen when we don't trust the leaf mask (auto color mask).
            # A user-defined poly or SAM box is trusted, so never widen those.
            lesion = model_lesion
            leaf = leaf | model_lesion
    else:
        lesion = segment_disease_mask(bgr, leaf)
        lesion_src = "color"

    return leaf, lesion, f"{leaf_src}+{lesion_src}"


@dataclass
class SeverityResult:
    severity_percent: float
    leaf_pixels: int
    diseased_pixels: int
    method: str = "color"   # "model" (trained segmenter) or "color" (fallback)


def make_overlay(image, leaf_color=(60, 200, 90), disease_color=(230, 40, 40),
                 alpha=0.45, box=None, polygon=None):
    """Build an RGB overlay visualizing the leaf mask and diseased pixels.

    - Leaf (healthy) pixels are tinted green.
    - Diseased pixels are tinted red.
    - Background is dimmed so the leaf stands out.

    Returns an RGB uint8 numpy array (H, W, 3).
    """
    import cv2

    bgr = _to_bgr_uint8(image)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

    leaf, diseased, _method = compute_masks(bgr, box=box, polygon=polygon)
    healthy = leaf & (~diseased)

    out = rgb.copy()

    # Dim the background.
    bg = ~leaf
    out[bg] = out[bg] * 0.35

    # Tint healthy leaf green.
    lc = np.array(leaf_color, dtype=np.float32)
    out[healthy] = (1 - alpha) * out[healthy] + alpha * lc

    # Tint diseased red.
    dc = np.array(disease_color, dtype=np.float32)
    out[diseased] = (1 - alpha) * out[diseased] + alpha * dc

    # Draw a crisp contour around diseased regions for clarity.
    dmask = (diseased.astype(np.uint8)) * 255
    contours, _ = cv2.findContours(dmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out_u8 = out.clip(0, 255).astype(np.uint8)
    cv2.drawContours(out_u8, contours, -1, (255, 255, 0), 1)

    return out_u8


def overlay_png_base64(image, box=None, polygon=None) -> str:
    """Return the overlay as a base64-encoded PNG data URI string (no prefix).

    The caller can prepend 'data:image/png;base64,' for use in an <img> tag.
    """
    import base64
    import cv2

    overlay = make_overlay(image, box=box, polygon=polygon)
    bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def measure_severity(image, box=None, polygon=None) -> SeverityResult:
    """Measure diseased-area severity for a leaf image via segmentation.

    Uses the trained lesion segmenter when available, else the color method.
    Leaf isolation: a free-form `polygon` (traced outline) takes priority, then
    a `box` (with MobileSAM), else the automatic color leaf mask.
    `image` may be a file path, a PIL Image, or a numpy array (RGB).
    Returns a SeverityResult with severity_percent in 0..100.
    """
    bgr = _to_bgr_uint8(image)
    leaf, lesion, method = compute_masks(bgr, box=box, polygon=polygon)
    leaf_pixels = int(leaf.sum())
    if leaf_pixels == 0:
        return SeverityResult(0.0, 0, 0, method)

    diseased_pixels = int(lesion.sum())
    severity = 100.0 * diseased_pixels / leaf_pixels
    return SeverityResult(severity, leaf_pixels, diseased_pixels, method)


# --------------------------------------------------------------------------- #
# Combined prediction
# --------------------------------------------------------------------------- #

def build_prediction(
    class_names: Sequence[str],
    probabilities: Sequence[float],
    image=None,
    box=None,
    polygon=None,
) -> Prediction:
    """Combine disease classification with segmentation-based severity.

    - Disease class + confidence come from the model's softmax `probabilities`.
    - Severity:
        * If the predicted class is "Healthy", severity = 0%.
        * Otherwise, if `image` is provided, severity is MEASURED via
          segmentation (measure_severity).
        * If no image is provided (e.g. a unit test), we fall back to
          confidence-scaled severity so the function still returns something.
    """
    probs = np.asarray(probabilities, dtype=float)
    best_idx = int(np.argmax(probs))
    predicted_class = class_names[best_idx]
    confidence = float(probs[best_idx])

    if _is_healthy(predicted_class):
        severity = 0.0
    elif image is not None:
        severity = measure_severity(image, box=box, polygon=polygon).severity_percent
    else:
        # Fallback proxy when no image is available.
        severity = confidence * 100.0

    return _assemble_prediction(predicted_class, confidence, severity)


def build_prediction_from_severity(class_names, probabilities, severity_percent):
    """Like build_prediction but with a PRE-MEASURED severity value.

    Use this when severity was already computed (e.g. by measure_severity with a
    box) to avoid running segmentation twice.
    """
    probs = np.asarray(probabilities, dtype=float)
    best_idx = int(np.argmax(probs))
    predicted_class = class_names[best_idx]
    confidence = float(probs[best_idx])
    severity = 0.0 if _is_healthy(predicted_class) else float(severity_percent)
    return _assemble_prediction(predicted_class, confidence, severity)


def _assemble_prediction(predicted_class, confidence, severity) -> Prediction:
    note = ""
    low_conf = False

    # Guard 1 - severity floor: a few stray diseased specks on an otherwise
    # green leaf shouldn't be called a disease. Treat as Healthy -> no spray.
    if not _is_healthy(predicted_class) and 0.0 < severity < MIN_SEVERITY_PERCENT:
        note = (f"diseased area {severity:.2f}% is below the {MIN_SEVERITY_PERCENT}% "
                f"floor - treated as healthy (no spray)")
        predicted_class = "Healthy"
        severity = 0.0

    # Guard 2 - confidence gate: if the classifier is unsure, don't assert a
    # disease as if it were certain. Flag it and neutralize the disease factor.
    if not _is_healthy(predicted_class) and confidence < MIN_CONFIDENCE:
        low_conf = True
        note = (note + " | " if note else "") + \
               (f"low confidence ({confidence*100:.0f}%) - prediction uncertain")

    code, name, base_coeff = severity_to_category(severity)
    # Disease-specific dosing: the CNN's class scales the base coefficient so
    # the diagnosed disease genuinely affects how much is sprayed.
    factor = disease_treatment_factor(predicted_class)
    effective_coeff = max(0.0, min(1.0, base_coeff * factor))
    return Prediction(
        disease_class=predicted_class,
        confidence=confidence,
        severity_percent=severity,
        category=name,
        category_code=code,
        reduction_coefficient=effective_coeff,
        base_coefficient=base_coeff,
        disease_factor=factor,
        low_confidence=low_conf,
        note=note,
    )


# ---------------------------------------------------------------------------
# Spray timing.
#
# The base paper (Tewari et al., 2020) computes a per-hill chemical volume
#     a  = (C * A) / (d * 10)     [mL/hill]
#     ts = a / Qs                 [s]
# but with typical values (A=500 L/ha, d=25 hills/m^2, Qs=3.5 mL/s) this yields
# sub-second times that are unrealistically short and hard to visualize.
#
# Real variable-rate / PWM sprayers operate their solenoid open windows on the
# order of ~0.5 s (minimum meaningful pulse) up to ~3 s for a full-open dose:
#   - PWM sprayers pulse valves ~10 Hz; effective dose = duty cycle x window
#     (UNL Extension G2302).
#   - Proportional-valve field sprayers use ~3 s full open/close
#     (Agriculture 2024, 14(3), 361).
#
# So we standardize ts to a realistic window scaled by the effective
# coefficient C_eff in [0, 1]:
#       ts = TS_MIN + C_eff * (TS_MAX - TS_MIN)     (0 when C_eff == 0)
# Defaults: TS_MIN = 0.5 s, TS_MAX = 3.0 s. Overridable via env for calibration.
# ---------------------------------------------------------------------------
SPRAY_TS_MIN = float(os.environ.get("SPRAY_TS_MIN", "0.5"))   # seconds
SPRAY_TS_MAX = float(os.environ.get("SPRAY_TS_MAX", "3.0"))   # seconds


def spray_time(coefficient: float, app_rate_lph: float = 500.0,
               hill_density: float = 25.0, flow_rate_mls: float = 3.5) -> float:
    """Solenoid open time ts (seconds) for a given effective coefficient.

    Standardized to a realistic actuation window (SPRAY_TS_MIN..SPRAY_TS_MAX)
    scaled linearly by the effective coefficient C_eff in [0, 1]:

        ts = 0                                   if C_eff <= 0  (healthy, no spray)
        ts = TS_MIN + C_eff * (TS_MAX - TS_MIN)  otherwise

    The app_rate/hill_density/flow_rate args are retained for API compatibility
    and reporting (per-hill volume a = C*A/(d*10)) but no longer drive ts, since
    the raw base-paper ts is sub-second and unrealistic for a real valve.
    """
    c = max(0.0, min(1.0, float(coefficient)))
    if c <= 0.0:
        return 0.0
    return SPRAY_TS_MIN + c * (SPRAY_TS_MAX - SPRAY_TS_MIN)


if __name__ == "__main__":
    # quick self-check of the disease-specific dosing (no image needed).
    # Same severity, different disease -> different effective coefficient.
    names = ["Bacterial_Blight", "Brown_Spot", "Leaf_Smut"]
    for i, nm in enumerate(names):
        probs = [0.1, 0.1, 0.1]
        probs[i] = 0.9
        # force a fixed severity via the no-image fallback (confidence*100=90 -> High)
        pred = build_prediction(names, probs)
        d = pred.to_dict()
        print(f"{nm:18s} base_C={d['base_coefficient']} x factor={d['disease_factor']} "
              f"-> effective_C={d['reduction_coefficient']}")
