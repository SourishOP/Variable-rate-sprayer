# notebooks: Colab training notebooks

| Notebook | Trains | Script it runs |
|----------|--------|----------------|
| `main_model.ipynb` | 6-class EfficientNetV2-B0 disease classifier | `model/colab_train_merged.py` |
| `segmenter_model.ipynb` | Binary lesion segmentation U-Net on PlantSeg | `model/colab_train_segmenter.py` |

Both were run on a Google Colab T4 GPU and keep their recorded outputs.

## Use

1. Open the notebook in Google Colab and select a GPU runtime.
2. For `main_model.ipynb`, set your own Kaggle token in the first cell
   (`KAGGLE_API_TOKEN`). The repository version contains a placeholder. Never
   commit a real token.
3. Paste the contents of the matching script from `model/` where the notebook
   asks for it, run the probe cell first (`PROBE_ONLY=1`), then the training
   cell.
4. Download the produced `.keras` file into `model/`.

See [../docs/model_run_instructions.md](../docs/model_run_instructions.md) for
the options of each script.

Back to the [main README](../README.md).