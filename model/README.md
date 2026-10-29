# model: inference code, training scripts and weights

| File | Purpose |
|------|---------|
| `severity.py` | Leaf and lesion segmentation, severity %, level, dosing and spray-time mapping |
| `predict.py` | Single-image command line prediction |
| `colab_train_merged.py` | Colab script: merges the UCI paddy set and an open HuggingFace set, trains the 6-class EfficientNetV2-B0 |
| `colab_train_segmenter.py` | Colab script: trains the binary lesion U-Net (MobileNetV2 encoder) on PlantSeg |
| `class_names.txt` | Class order: Bacterial_Blight, Blast, Brown_Spot, Healthy, Leaf_Smut, Neck_Blast |
| `requirements.txt` | Dependencies for training and inference |
| `rice_disease_effnetv2b0.keras` | Trained classifier (Git LFS) |
| `lesion_segmenter.keras` | Trained lesion segmenter (Git LFS) |
| `mobile_sam.pt` | MobileSAM weights for interactive leaf isolation (Git LFS) |

The three weight files are tracked with Git LFS. After cloning run
`git lfs pull`.

## Predict

```bash
pip install -r model/requirements.txt
python model/predict.py --image data/sample_images/Brown_Spot/Brown_Spot_01.jpg
python model/predict.py --image leaf.jpg --save_overlay overlay.png
```

If a trained segmenter is missing, `severity.py` falls back to colour-threshold
segmentation. Thresholds can be set with `MIN_SEVERITY_PERCENT` (default 1.5),
`MIN_CONFIDENCE` (0.70), `SEG_THRESHOLD` (0.5), `SPRAY_TS_MIN` (0.5 s) and
`SPRAY_TS_MAX` (3.0 s).

## Train

Training runs on Google Colab with a GPU. Use the notebooks in
[../notebooks](../notebooks/README.md) and the walkthrough in
[../docs/model_run_instructions.md](../docs/model_run_instructions.md).

Back to the [main README](../README.md).