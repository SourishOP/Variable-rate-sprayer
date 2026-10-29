# data: sample images

`sample_images/` holds 49 test leaf photos (9 to 10 per class), used by the pipeline and
API tests in `report/build/` and handy for trying the demo.

| Folder | Class |
|--------|-------|
| `Bacterial_Blight/` | Bacterial blight |
| `Brown_Spot/` | Brown spot |
| `healthy/` | Healthy |
| `leaf_smut/` | Leaf smut |
| `Neck Blast/` | Neck blast |

These are not the training sets. Training data is downloaded by the Colab
scripts in [../model](../model/README.md). The images come from public rice
leaf datasets and keep their original licenses.

Try one:

```bash
python model/predict.py --image "data/sample_images/Neck Blast/Neck_Blast_04.jpg"
```

Back to the [main README](../README.md).