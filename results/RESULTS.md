# PaddyGuard — Results Obtained So Far

Interim results for Review III. All numbers are from held-out validation/test
data (not training data). Two trained deep-learning models plus a classical +
learned severity pipeline are implemented and running end-to-end in a live web
app.

---

## 1. System overview

| Module | Method | Status |
|--------|--------|--------|
| Disease classification | EfficientNetV2-B0 (transfer learning, fine-tuned) | Trained, deployed |
| Lesion segmentation | U-Net (MobileNetV2 encoder), Dice + BCE loss | Trained, deployed |
| Leaf isolation (interactive) | MobileSAM (box / free-form outline prompt) | Deployed |
| Severity measurement | diseased pixels ÷ leaf pixels × 100 | Deployed |
| Variable-rate spray | severity → coefficient → solenoid open time | Deployed |

---

## 2. Disease classifier — accuracy

The classifier was trained in two stages (frozen backbone, then fine-tuning)
with class weighting to handle imbalance.

### 2a. Initial 3-class model (UCI paddy dataset)
Held-out **test set: 164 images the model never saw**.

| Metric | Value |
|--------|-------|
| Overall test accuracy | **91.5%** |
| Bacterial leaf blight | precision 1.00 · recall 1.00 · F1 1.00 |
| Brown spot | precision 0.86 · recall 0.89 · F1 0.87 |
| Leaf smut | precision 0.89 · recall 0.85 · F1 0.87 |

Interpretation: bacterial leaf blight is classified perfectly; the small error
is Brown spot ↔ Leaf smut, which are visually similar. Visible on the confusion
matrix.

### 2b. Merged 6-class model (adds a Healthy class + Blast/Neck Blast)
To remove the "healthy leaf misclassified as a disease" problem, two datasets
were merged (UCI + an open HuggingFace rice set), giving 6 classes:

| Class | Training images | Notes |
|-------|-----------------|-------|
| Healthy | 1,488 | well represented |
| Blast | 977 | well represented |
| Neck_Blast | 1,000 | well represented |
| Brown_Spot | 667 | well represented |
| Bacterial_Blight | 55 | **data-thin (limitation)** |
| Leaf_Smut | 55 | **data-thin (limitation)** |

Total: 4,242 images, 80/20 train/val split with class weights.

**Measured on the held-out validation set (815 images) of the merged model:**

| Metric | Value |
|--------|-------|
| Overall accuracy | **83.80%** (683 / 815) |
| Macro avg F1 | 0.82 |
| Weighted avg F1 | 0.84 |

Per-class (validation):

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| Neck_Blast | 1.00 | 1.00 | 1.00 | 206 |
| Healthy | 0.83 | 0.88 | 0.85 | 288 |
| Brown_Spot | 0.73 | 0.74 | 0.73 | 126 |
| Blast | 0.74 | 0.67 | 0.71 | 195 |

Interpretation: Neck blast is classified perfectly and Healthy is strong (0.85 F1)
— the practically important "spray vs. don't spray" decision is reliable. Blast and
Brown spot are the weaker pair (F1 ~0.71–0.73), as they share tan/brown lesion
appearance. The two data-thin classes (Bacterial Blight, Leaf Smut — 55 training
images each) were not present in this validation subset and remain the known
limitation. For reference, the earlier 3-class model (section 2a, on a dataset
where every class had enough data) reached 91.5% — showing the architecture
performs well when class data is sufficient.

---

## 3. Lesion segmentation — quality

Trained on PlantSeg (Wei et al., 2024; open Zenodo record 14935094, CC BY 4.0),
which provides expert pixel masks. Binary lesion segmentation (diseased vs not),
U-Net with Dice + BCE loss, IoU metric.

Measured on the full PlantSeg validation set (**1,247 images**):

| Metric | Value |
|--------|-------|
| Validation IoU (mean) | **0.4450** |
| Validation Dice (mean) | **0.5641** |

Context: in-the-wild lesion segmentation is a hard problem — the PlantSeg paper's
own best baseline (SegNext, MSCAN-L) reaches **~44.5% mIoU** with a much heavier
model, and DeepLabV3+ reaches only ~25–27%. Our lightweight binary U-Net
(MobileNetV2 encoder) achieves **0.445 IoU — on par with the paper's strongest
baseline** while being far smaller, and it clearly outperforms the classical
colour-threshold method on cluttered field photos.

---

## 4. Severity → variable-rate spray mapping

Severity (measured from segmentation) sets a base coefficient; the diagnosed
disease then scales the dose. Solenoid open time is standardized to a realistic
valve window (0.5–3.0 s), consistent with PWM / proportional-valve sprayers.

| Severity S (%) | Level | Base C | Example (Bacterial blight ×1.2) | Spray time t_s |
|----------------|-------|--------|--------------------------------|----------------|
| 0 (Healthy)    | Healthy | 0.00 | 0.00 | 0.00 s (no spray) |
| 0.1 – 5        | Low     | 0.30 | 0.36 | ~1.4 s |
| 5.1 – 20       | Medium  | 0.55 | 0.66 | ~2.15 s |
| > 20           | High    | 0.80 | 0.96 | ~2.9 s |

Disease-specific factors: Bacterial blight ×1.20, Neck blast ×1.25, Blast ×1.15,
Brown spot ×1.00, Leaf smut ×0.80, Healthy ×0.00.

Equations (base paper, Tewari et al. 2020):
`a = (C_eff × A) / (d × 10)` mL/hill · `t_s` standardized to the valve window.

---

## 5. How the metrics are calculated (methodology)

All numbers above are **measured on a held-out validation split** (20% of the
data, chosen with a fixed seed so it never overlaps the training images). No
number is estimated.

### 5a. Classifier accuracy

Accuracy = (correctly predicted images) ÷ (total images). For each validation
image, the model outputs a probability over the classes; the predicted class is
the `argmax`. It is counted correct if that equals the true label.

```python
# 20% held-out validation split (fixed seed -> disjoint from training)
vds = tf.keras.utils.image_dataset_from_directory(
    data_dir, validation_split=0.2, subset="validation", seed=123,
    image_size=(224, 224), batch_size=32, label_mode="categorical")

correct, total = 0, 0
y_true, y_pred = [], []
for images, labels in vds:
    preds = model.predict(images, verbose=0)          # softmax probabilities
    for i in range(len(images)):
        true_idx = int(np.argmax(labels[i].numpy()))   # ground-truth class
        pred_idx = int(np.argmax(preds[i]))            # predicted class
        y_true.append(true_idx); y_pred.append(pred_idx)
        total += 1
        correct += (pred_idx == true_idx)

accuracy = correct / total                             # overall accuracy

# Per-class precision / recall / F1 and the confusion matrix
from sklearn.metrics import classification_report, confusion_matrix
print(classification_report(y_true, y_pred))
cm = confusion_matrix(y_true, y_pred)
```

- **Precision** (per class) = TP ÷ (TP + FP) — of everything predicted as this
  disease, how much was right.
- **Recall** (per class) = TP ÷ (TP + FN) — of all actual cases of this disease,
  how many were caught.
- **F1** = harmonic mean of precision and recall.
- **Confusion matrix** — rows = true class, columns = predicted class; the
  diagonal is correct predictions, off-diagonal shows which classes get confused.

### 5b. Segmentation IoU and Dice

Segmentation quality compares the predicted lesion mask against the expert
ground-truth mask, pixel by pixel. For each image:

```python
# ground-truth mask (from COCO polygons) vs model prediction
pred = seg_model.predict(inp, verbose=0)[0, :, :, 0]   # per-pixel probability
pred_mask = (pred > 0.5).astype(np.uint8)              # threshold -> binary mask

intersection = np.sum(gt_mask * pred_mask)             # overlap pixels
union        = np.sum((gt_mask + pred_mask) > 0)       # combined pixels

iou  = intersection / union                            # Jaccard index (IoU)
dice = 2 * intersection / (np.sum(gt_mask) + np.sum(pred_mask))   # Dice / F1
```

- **IoU (Intersection over Union)** = overlap ÷ combined area. 1.0 = perfect,
  0 = no overlap. Reported value is the mean IoU over all 1,247 validation images.
- **Dice** = 2 × overlap ÷ (predicted + true area) — same idea, weights overlap
  more; equivalent to the pixel-level F1 score.

The 0.5 threshold turns the model's per-pixel probability into a hard lesion/
not-lesion decision before comparing to the ground truth.

---

## 6. Robustness / honesty features (implemented)

- **Confidence gate (0.70):** low-confidence predictions are flagged "uncertain"
  rather than asserted, since a sub-70% top score on 6 classes is a weak guess.
- **Severity floor (1.5%):** a few stray diseased specks on an otherwise green
  leaf are treated as Healthy (no spray) — removes false positives.
- **Graceful fallbacks:** trained segmenter → colour method; SAM leaf isolation →
  automatic leaf mask, if a component is unavailable.

---

## 7. Known limitations (future work)

1. **Two data-thin classes** (Bacterial blight, Leaf smut: 55 images each) are
   the weakest — more balanced data is the primary next step.
2. **Field-photo segmentation** is imperfect on very cluttered backgrounds;
   free-form leaf tracing mitigates this.
3. **Spray timing window (0.5–3.0 s)** is a research-backed default, not yet
   calibrated to a specific physical pump/nozzle.

---

## 8. What is demonstrable live

Upload a rice leaf → the app shows: segmented mask overlay, disease class +
confidence, measured severity %, the severity formula walkthrough, disease-
specific dosing, and an animated solenoid open-time. Past analyses are saved in
the History tab.

Command: `python app/server.py` → open <http://127.0.0.1:5000>
