# Model Run Guide (Train, Predict, Demo)

This guide covers the software side: training the disease classifier and the
lesion segmenter, running single-image prediction, and running the web demo.
The hardware side is documented in [../hardware](../hardware/README.md) and
[../firmware](../firmware/README.md).

## How it works

1. **Disease classification.** An `EfficientNetV2-B0` (transfer learning)
   predicts one of six classes: `Bacterial_Blight`, `Blast`, `Brown_Spot`,
   `Healthy`, `Leaf_Smut`, `Neck_Blast` (order in `model/class_names.txt`).
2. **Severity measurement.** `model/severity.py` isolates the leaf and the
   lesion pixels (trained U-Net lesion segmenter, with a colour-threshold
   fallback; optional MobileSAM leaf isolation) and computes:

   ```
   severity_percent = 100 * diseased_pixels / leaf_pixels
   ```

   The percentage maps to a level and a base coefficient. A disease-specific
   factor then scales the dose (see `DISEASE_TREATMENT_FACTOR` in `severity.py`
   and [../results/RESULTS.md](../results/RESULTS.md) section 4).

   | Severity %      | Level    | Base coefficient |
   |-----------------|----------|------------------|
   | model = Healthy | Healthy  | 0.00             |
   | 0.1 - 5%        | Low      | 0.30             |
   | 5.1 - 20%       | Medium   | 0.55             |
   | > 20%           | High     | 0.80             |

   Severity below 1.5% is treated as Healthy, and classifier confidence below
   0.70 is flagged as uncertain. Both thresholds are environment-overridable
   (`MIN_SEVERITY_PERCENT`, `MIN_CONFIDENCE`).

Severity is measured from pixels, not derived from classifier confidence.

---

## Files

| File | Purpose |
|------|---------|
| `model/colab_train_merged.py`    | Colab script: merges the UCI paddy set (Kaggle) with an open HuggingFace rice set and trains the 6-class classifier |
| `model/colab_train_segmenter.py` | Colab script: trains the binary lesion U-Net on PlantSeg |
| `model/severity.py`              | Segmentation-based severity, dosing and spray-time mapping |
| `model/predict.py`               | Single-image inference (disease + severity) |
| `model/class_names.txt`          | Class order used by the classifier |
| `model/requirements.txt`         | Python dependencies |
| `notebooks/main_model.ipynb`     | Colab notebook that runs `colab_train_merged.py` |
| `notebooks/segmenter_model.ipynb`| Colab notebook that runs `colab_train_segmenter.py` |

Trained weights (`*.keras`, `mobile_sam.pt`) are stored with Git LFS. Run
`git lfs pull` after cloning.

---

## A. Train the classifier in Google Colab

The easiest route is `notebooks/main_model.ipynb`: open it in Colab with a GPU
runtime (**Runtime > Change runtime type > GPU, T4**) and run the cells.

To run it by hand:

1. Create a Kaggle token (kaggle.com > **Settings > API > Create New API
   Token**) and set it in the session. Never commit or paste it anywhere
   public. If it leaks, expire it in the same settings page.

   ```python
   import os
   os.environ["KAGGLE_API_TOKEN"] = "KGAT_...your token..."
   ```

2. Paste `model/colab_train_merged.py` into a cell with
   `%%writefile /content/train_merged.py`, then run it:

   ```python
   # Optional: merge datasets and print class counts only
   os.environ["PROBE_ONLY"] = "1"
   !python /content/train_merged.py

   os.environ["PROBE_ONLY"] = "0"
   !python /content/train_merged.py
   ```

   Optional environment variables: `KAGGLE_DATASET` (default
   `badhon7432/paddyleafdiseaseuci`), `HF_ZIP_URL`, `EPOCHS`, `FT_EPOCHS`,
   `BATCH`, `OUT_DIR`.

3. Download the outputs (`rice_disease_effnetv2b0.keras`, `class_names.txt`)
   into `model/`.

The classifier is trained in two stages (frozen backbone, then fine-tuning)
with class weights to offset class imbalance.

---
## B. Predict on a single image

After training (model + `class_names.txt` present in `model/`):

```bash
pip install -r model/requirements.txt
python model/predict.py --image path/to/leaf.jpg
```

Example output:

```json
{
  "disease_class": "Brown_Spot",
  "confidence": 0.97,
  "severity_percent": 8.45,
  "category": "Medium",
  "category_code": 2,
  "reduction_coefficient": 0.55
}
```

To also save a visualization of the diseased area:

```bash
python model/predict.py --image leaf.jpg --save_overlay overlay.png
```

`overlay.png` highlights the pixels counted as diseased in red.

---

## Tips for best accuracy

- **More data is the biggest lever.** Prefer a dataset with 500+ images/class.
  Small sets (like the 40-image UCI set) overfit quickly.
- Keep the two-stage training (frozen head, then fine-tune) — it's already set up.
- Watch `confusion_matrix.png`: if two diseases get confused, add more examples
  of those, or increase `--fine_tune_epochs`.
- The severity segmenter assumes leaf-filling photos on a plain-ish background.
  Very cluttered backgrounds reduce leaf-mask accuracy. For consistent severity,
  photograph a single leaf against a neutral background.
- Severity thresholds (5% / 20%) live in `severity.py:severity_to_category`.
  Adjust them if your agronomy guidance differs.

---

## Quick local test (no model needed)

Verify the severity mapping logic runs:

```bash
python model/severity.py
```

It prints a Healthy and a diseased example mapping.

---

## C. Demo for your panel (PaddyGuard web UI)

An interactive, presentation-ready web UI lives in `app/`. Drag in a leaf photo
and it shows, live:

1. The **segmented mask PNG** (green = healthy tissue, red = diseased pixels).
2. The **disease class** + confidence.
3. An animated **severity calculation** walkthrough (pixels → ratio → % → level).
4. An animated **solenoid open-time** (`ts`) visualization with a spraying hose.

It works even before training: if no trained model is present it runs in
**demo mode** (the disease label is a heuristic, but the severity % is still
really measured from the mask). Once `model/rice_disease_effnetv2b0.keras`
exists, it automatically runs in full **model mode**.

### Run locally (Windows / macOS / Linux)

```bash
pip install -r app/requirements.txt
python app/server.py
```

Then open <http://127.0.0.1:5000> in your browser and drag in a leaf image.

> Tip: put the trained `rice_disease_effnetv2b0.keras` and `class_names.txt`
> in the `model/` folder to demo with the real classifier. Otherwise set the
> path with the `MODEL_PATH` environment variable.

### Run in Google Colab with a public URL (present from anywhere)

```python
!pip install -q -r app/requirements.txt pyngrok
# (optional, for a stable tunnel) set your free ngrok token:
# from pyngrok import conf; conf.get_default().auth_token = "YOUR_NGROK_TOKEN"
!python app/launch_colab.py
```

It prints a public HTTPS URL. Open it on the projector or share it with the
panel; the UI runs from their browser.

### What to say while presenting

- "The model classifies the disease; severity is **measured** by segmenting the
  diseased area, not guessed from confidence."
- Point at the red mask overlay: "these red pixels are the lesion area the
  system counts."
- Walk through the on-screen formulas: `S = diseased ÷ leaf × 100`, then
  `a = (C·A)/(d·10)` and `ts = a / Qs`.
- The hose animation shows the valve staying open for `ts` seconds, proportional
  to severity. Healthy leaf ⇒ no spray.

### Tuning the spray numbers live

The spray equation inputs can be overridden per request (defaults A=500, d=25,
Qs=3.5). For example to reflect your calibration, append query params to the
predict call, or set env vars before launching:

```bash
APP_RATE_LPH=450 HILL_DENSITY=30 FLOW_RATE_MLS=4.0 python app/server.py
```

### Files

| File | Purpose |
|------|---------|
| `app/server.py`        | Flask backend (`/`, `/health`, `/predict`) |
| `app/static/index.html`| The full UI (drag-drop, mask, animations) |
| `app/launch_colab.py`  | Background server + public ngrok URL for Colab |
| `app/requirements.txt` | UI/demo dependencies |

---

## D. (Optional, advanced) Trained lesion segmentation model — "Option C"

The default severity uses a **color-based** segmentation that works well on a
single leaf against a plain background but struggles on cluttered field photos
(it can mark naturally-brown healthy tissue as diseased, or miss lesions when
the background is busy).

For robust masks you can train a real **lesion segmentation model** on
**PlantSeg** (Wei et al., 2024) — a large in-the-wild dataset with expert
pixel masks. Once trained, drop the model into `model/` and the app uses it
automatically; otherwise it silently falls back to the color method.

> **Which PlantSeg record:** use the **open** Zenodo record
> [`14935094`](https://zenodo.org/records/14935094) (`plantsegv3.zip`, ~1.7 GB,
> **COCO-format** polygon annotations, **CC BY 4.0**). The older record
> `13293891` is access-restricted and will not download.

### Train it (Colab GPU)

Paste the contents of `model/colab_train_segmenter.py` into a cell using
`%%writefile /content/train_seg.py`, then run it. The script downloads
`plantsegv3.zip`, rasterizes the COCO polygons into binary lesion masks, and
trains a U-Net.

```python
# 1) (optional) probe the archive structure first
import os
os.environ["PROBE_ONLY"] = "1"
!python /content/train_seg.py       # prints JSONs + image dirs, then exits

# 2) train (all categories = general lesion segmenter, best for robustness)
os.environ["PROBE_ONLY"] = "0"
# os.environ["CATEGORY_FILTER"] = "rice"   # optional: rice-only
!python /content/train_seg.py
```

By default it trains on **all** disease categories (a general lesion segmenter,
which is more robust for rice severity). Set `CATEGORY_FILTER="rice"` to use only
rice categories. Use `MAX_IMAGES=800` for a quick first run.

It saves `lesion_segmenter.keras` to `/content/seg_outputs`. Download it:

```python
from google.colab import files
files.download("/content/seg_outputs/lesion_segmenter.keras")
```

### Use it locally

Put `lesion_segmenter.keras` in the `model/` folder (next to
`rice_disease_effnetv2b0.keras`). Restart the server:

```bash
python app/server.py
```

The mask panel will now say "trained lesion model (PlantSeg)" instead of
"color method". No code changes needed — `severity.py` detects the file.

### Honest expectations

Pixel-level disease segmentation in the wild is hard: the PlantSeg paper's own
best baseline reaches ~44% mIoU. Our binary lesion U-Net will noticeably beat
the color method on messy photos but will not produce perfect masks. For the
cleanest demo visuals, still prefer single-leaf, plain-background images.

### If the download or archive layout differs

The script auto-discovers the COCO JSONs and image folders. If it can't find
them, run once with `PROBE_ONLY=1` (see above) and share the printed structure
so the paths can be adjusted. To point at a different archive URL:

```python
import os
os.environ["ZENODO_URL"] = "https://zenodo.org/api/records/14935094/files/plantsegv3.zip/content"
```

---

## E. (Optional) Interactive leaf isolation with MobileSAM — "Option B"

On cluttered field photos the automatic (color) leaf detector can grab the
background instead of the main leaf, which throws off severity. Option B lets
you **draw a box around the main leaf** in the UI; MobileSAM then segments just
that leaf, and lesion detection + severity run only inside it.

### Enable it

```bash
pip install ultralytics      # adds MobileSAM support (PyTorch)
python app/server.py
```

The first time you use a box, ultralytics downloads the small `mobile_sam.pt`
weights (~40 MB) automatically. If `ultralytics` is not installed, the app
silently falls back to the color leaf mask (no error).

### Use it

1. Upload a leaf image (it analyzes automatically with the color leaf mask).
2. **Drag a rectangle** around the main leaf on the "Original" image.
3. Click **"Analyze selected leaf"**.
4. The mask panel's segmentation line will read `sam+model` (leaf isolated by
   MobileSAM, lesions by the trained model).

### Honest notes

- MobileSAM runs on CPU in a few seconds per image — fine for a demo, not
  instant. A GPU makes it much faster.
- SAM isolates whatever leaf your box covers; draw the box tightly around the
  single leaf you want assessed.
- This does not make in-the-wild lesion detection perfect, but it fixes the most
  common failure (background counted as leaf) and makes severity meaningful on
  cluttered photos.
