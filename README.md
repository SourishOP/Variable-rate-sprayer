# Rice Leaf Disease Detection & Severity Grading

Upload a picture of a paddy (rice) leaf and get:

1. **Disease class** — `Bacterial_Blight`, `Brown_Spot`, `Healthy`, `Leaf_Smut`
2. **Severity level** — Healthy / Low / Medium / High, from a **measured**
   diseased-area percentage.

This is a model-only project (no hardware).

---

## How it works

**1. Disease classification** — `EfficientNetV2-B0` (transfer learning) predicts
the disease class.

**2. Severity measurement** — for a diseased leaf, the leaf and its lesion pixels
are segmented with classical computer vision and severity is computed as:

```
severity_percent = 100 * diseased_pixels / leaf_pixels
```

| Severity %      | Level    | Coefficient |
|-----------------|----------|-------------|
| model = Healthy | Healthy  | 0.00        |
| 0.1 – 5%        | Low      | 0.33        |
| 5.1 – 20%       | Medium   | 0.67        |
| > 20%           | High     | 1.00        |

Severity is measured, not a confidence proxy.

---

## Layout

```
Variable Rate Sprayer/
├── model/
│   ├── train_efficientnetv2.py   # EfficientNetV2-B0 trainer
│   ├── severity.py               # segmentation-based severity + mask overlay
│   ├── predict.py                # single-image inference (CLI)
│   ├── colab_setup.py            # Kaggle download + launch training (Colab)
│   └── requirements.txt
├── app/                          # interactive demo UI for the panel
│   ├── server.py                 # Flask backend (/predict, serves the UI)
│   ├── static/index.html         # drag-drop UI, live mask + animations
│   ├── launch_colab.py           # public URL launcher for Colab
│   └── requirements.txt
├── docs/
│   └── model_run_instructions.md # train + predict + demo walkthrough
└── README.md
```

---

## Quick start

Train (Google Colab with GPU recommended):

```python
!pip install -q -r model/requirements.txt
!python model/colab_setup.py --upload_token --download --train --epochs 25
```

Predict on one image:

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
  "reduction_coefficient": 0.67
}
```

### Interactive demo UI (for a project review / panel)

```bash
pip install -r app/requirements.txt
python app/server.py     # open http://127.0.0.1:5000
```

Drag in a leaf photo to see the live mask, disease + measured severity, the
severity formulas animating, and a spray hose that opens for the computed time.
Works in demo mode before training; uses the real model once it exists.

See `docs/model_run_instructions.md` for the full walkthrough, dataset options,
accuracy tips, and the panel demo guide (section C).
