"""
ALL-IN-ONE Colab script: train a BINARY LESION SEGMENTATION model on PlantSeg.

"Option C" - a real trained segmentation model that outputs, per pixel, whether
it is diseased (lesion) or not. Severity then = predicted lesion pixels / leaf
pixels, instead of the color-threshold heuristic.

DATASET: PlantSeg (Wei et al., 2024), OPEN Zenodo record 14935094 (plantsegv3.zip,
~1.7 GB, COCO-format polygon annotations). License CC BY 4.0.
    https://zenodo.org/records/14935094

The archive ships COCO annotation JSONs (train/val/test) plus images. We
rasterize the polygon annotations into BINARY lesion masks (any annotated
disease region = 1, background = 0) and train a U-Net.

USAGE in Colab (GPU runtime) - paste this whole file into a cell via
%%writefile /content/train_seg.py, then:  !python /content/train_seg.py

    # optional: only rice categories (else trains a general lesion segmenter)
    # os.environ["CATEGORY_FILTER"] = "rice"

Config via env vars (all optional):
    ZENODO_URL       archive URL (default = open record 14935094)
    CATEGORY_FILTER  comma keywords to keep (default "" = all categories)
    IMG_SIZE         training resolution (default 256)
    EPOCHS           (default 40)
    BATCH            (default 16)
    MAX_IMAGES       cap images for a fast run (default 0 = use all)
    OUT_DIR          (default /content/seg_outputs)
    PROBE_ONLY       "1" to only print the archive structure and exit
"""

import glob
import json
import os
import subprocess
import sys


ZENODO_URL = os.environ.get(
    "ZENODO_URL",
    "https://zenodo.org/api/records/14935094/files/plantsegv3.zip/content",
)
DATA_ROOT = "/content/plantsegv3"
CATEGORY_FILTER = os.environ.get("CATEGORY_FILTER", "")
IMG_SIZE = int(os.environ.get("IMG_SIZE", "256"))
EPOCHS = int(os.environ.get("EPOCHS", "40"))
BATCH = int(os.environ.get("BATCH", "16"))
MAX_IMAGES = int(os.environ.get("MAX_IMAGES", "0"))
OUT_DIR = os.environ.get("OUT_DIR", "/content/seg_outputs")
PROBE_ONLY = os.environ.get("PROBE_ONLY", "0") == "1"


def sh(cmd):
    print("+", cmd)
    subprocess.check_call(cmd, shell=True)


def pip_install():
    print("[setup] installing packages...")
    sh(f"{sys.executable} -m pip install -q -U tensorflow numpy pillow "
       f"opencv-python-headless matplotlib pycocotools")


# --------------------------------------------------------------------------- #
# Download + extract
# --------------------------------------------------------------------------- #
def download():
    os.makedirs(DATA_ROOT, exist_ok=True)
    zip_path = os.path.join(DATA_ROOT, "plantsegv3.zip")
    have_json = glob.glob(os.path.join(DATA_ROOT, "**", "*.json"), recursive=True)
    if have_json:
        print("[download] data already extracted, skipping.")
        return
    if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 1_000_000:
        print(f"[download] {ZENODO_URL}  (~1.7 GB, be patient)")
        sh(f'curl -L -C - -o "{zip_path}" "{ZENODO_URL}"')
    print("[extract] unzipping...")
    # Some zips fail with `unzip`; fall back to python's zipfile.
    try:
        sh(f'unzip -q -o "{zip_path}" -d "{DATA_ROOT}"')
    except subprocess.CalledProcessError:
        print("[extract] unzip failed, using python zipfile...")
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(DATA_ROOT)
    print("[ok] extracted.")


def probe():
    """Print the archive layout: JSONs and image directories."""
    print("\n=== ARCHIVE STRUCTURE ===")
    jsons = glob.glob(os.path.join(DATA_ROOT, "**", "*.json"), recursive=True)
    print(f"JSON files ({len(jsons)}):")
    for j in jsons[:20]:
        print("  ", os.path.relpath(j, DATA_ROOT), f"({os.path.getsize(j)//1024} KB)")
    # image dirs
    img_dirs = {}
    for dp, _, files in os.walk(DATA_ROOT):
        n = sum(1 for f in files if f.lower().endswith((".jpg", ".jpeg", ".png")))
        if n:
            img_dirs[dp] = n
    print(f"\nImage directories ({len(img_dirs)}):")
    for d, n in sorted(img_dirs.items(), key=lambda x: -x[1])[:20]:
        print("  ", os.path.relpath(d, DATA_ROOT), f"-> {n} images")
    return jsons, img_dirs


# --------------------------------------------------------------------------- #
# Build (image, mask) pairs from COCO annotations
# --------------------------------------------------------------------------- #
def _pick_coco_json(jsons, want):
    """Pick the COCO json whose filename contains the split word `want`.

    PlantSeg v3 names them annotation_train.json / annotation_val.json /
    annotation_test.json. We match the split word as a whole token so "val"
    never accidentally matches inside another word.
    """
    import re
    # Prefer an exact "<something>_<want>.json" style match.
    for j in jsons:
        name = os.path.basename(j).lower()
        if re.search(rf"(^|[_\-]){want}(\.json$|[_\-.])", name):
            return j
    # Fallback: any json containing the split word.
    for j in jsons:
        if want in os.path.basename(j).lower():
            return j
    return None


def _find_image(img_dirs, file_name, split_word=None):
    """Locate the real photo for a COCO file_name.

    Prefer directories under images/ (and matching the split) so we never pick
    a same-named PNG from the annotations/ folder.
    """
    base = os.path.basename(file_name)
    stem = os.path.splitext(base)[0]

    def score(d):
        dl = d.replace("\\", "/").lower()
        s = 0
        if "/images/" in dl or dl.endswith("/images"):
            s += 2
        if "annotation" in dl:
            s -= 3
        if split_word and f"/{split_word}" in dl:
            s += 1
        return s

    ordered = sorted(img_dirs, key=score, reverse=True)
    for d in ordered:
        cand = os.path.join(d, base)
        if os.path.exists(cand):
            return cand
    for d in ordered:
        hits = glob.glob(os.path.join(d, stem + ".*"))
        if hits:
            return hits[0]
    return None


def build_pairs(jsons, img_dirs, split_word):
    """Return list of (image_path, coco, img_id) for a split, plus the coco obj."""
    from pycocotools.coco import COCO

    jpath = _pick_coco_json(jsons, split_word)
    if not jpath:
        return [], None, []
    print(f"[coco] {split_word}: {os.path.relpath(jpath, DATA_ROOT)}")
    coco = COCO(jpath)

    cats = coco.loadCats(coco.getCatIds())
    cat_names = {c["id"]: c["name"] for c in cats}
    print(f"[coco] {split_word}: {len(cats)} categories, "
          f"{len(coco.getImgIds())} images, {len(coco.getAnnIds())} annotations")

    # Optional category filter.
    filters = [t.strip().lower() for t in CATEGORY_FILTER.split(",") if t.strip()]
    keep_cat_ids = None
    if filters:
        keep_cat_ids = {cid for cid, nm in cat_names.items()
                        if any(t in nm.lower() for t in filters)}
        print(f"[coco] filter '{CATEGORY_FILTER}' -> categories: "
              f"{[cat_names[c] for c in keep_cat_ids]}")

    pairs = []
    for img_id in coco.getImgIds():
        info = coco.loadImgs(img_id)[0]
        img_path = _find_image(img_dirs, info["file_name"], split_word)
        if not img_path:
            continue
        ann_ids = coco.getAnnIds(imgIds=img_id)
        if keep_cat_ids is not None:
            anns = coco.loadAnns(ann_ids)
            if not any(a["category_id"] in keep_cat_ids for a in anns):
                continue
        pairs.append((img_path, img_id))
    return pairs, coco, keep_cat_ids


def coco_binary_mask(coco, img_id, keep_cat_ids, height, width):
    import numpy as np
    ann_ids = coco.getAnnIds(imgIds=img_id)
    anns = coco.loadAnns(ann_ids)
    mask = np.zeros((height, width), dtype=np.uint8)
    for a in anns:
        if keep_cat_ids is not None and a["category_id"] not in keep_cat_ids:
            continue
        m = coco.annToMask(a)
        if m.shape != (height, width):
            import cv2
            m = cv2.resize(m, (width, height), interpolation=cv2.INTER_NEAREST)
        mask = np.maximum(mask, m)
    return mask


# --------------------------------------------------------------------------- #
# tf.data pipeline (masks precomputed to PNG for speed)
# --------------------------------------------------------------------------- #
def materialize(pairs, coco, keep_cat_ids, split_dir):
    """Write resized image + binary mask pairs to disk once, return path list."""
    import cv2
    import numpy as np

    os.makedirs(split_dir, exist_ok=True)
    out = []
    n = len(pairs)
    if MAX_IMAGES:
        pairs = pairs[:MAX_IMAGES]
    for i, (img_path, img_id) in enumerate(pairs):
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        mask = coco_binary_mask(coco, img_id, keep_cat_ids, h, w)
        img_r = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
        mask_r = cv2.resize(mask, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_NEAREST)
        ip = os.path.join(split_dir, f"{i:06d}_img.png")
        mp = os.path.join(split_dir, f"{i:06d}_msk.png")
        cv2.imwrite(ip, img_r)
        cv2.imwrite(mp, (mask_r * 255).astype(np.uint8))
        out.append((ip, mp))
        if (i + 1) % 200 == 0:
            print(f"  materialized {i+1}/{min(n, len(pairs))}")
    print(f"[data] materialized {len(out)} pairs into {split_dir}")
    return out


def make_ds(pairs, training):
    import tensorflow as tf

    def load(ip, mp):
        img = tf.io.decode_png(tf.io.read_file(ip), channels=3)
        img = tf.cast(img, tf.float32)
        m = tf.io.decode_png(tf.io.read_file(mp), channels=1)
        m = tf.cast(tf.greater(m, 127), tf.float32)
        return img, m

    ips = [p[0] for p in pairs]
    mps = [p[1] for p in pairs]
    ds = tf.data.Dataset.from_tensor_slices((ips, mps))
    if training:
        ds = ds.shuffle(min(len(pairs), 1000))
    ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE)
    if training:
        def aug(img, m):
            if tf.random.uniform(()) > 0.5:
                img = tf.image.flip_left_right(img); m = tf.image.flip_left_right(m)
            if tf.random.uniform(()) > 0.5:
                img = tf.image.flip_up_down(img); m = tf.image.flip_up_down(m)
            return img, m
        ds = ds.map(aug, num_parallel_calls=tf.data.AUTOTUNE)
    return ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)


# --------------------------------------------------------------------------- #
# U-Net (MobileNetV2 encoder)
# --------------------------------------------------------------------------- #
def build_unet():
    import tensorflow as tf
    from tensorflow.keras import layers
    from tensorflow.keras.applications import MobileNetV2

    inputs = tf.keras.Input((IMG_SIZE, IMG_SIZE, 3))
    x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
    base = MobileNetV2(input_tensor=x, include_top=False, weights="imagenet")
    skip_names = ["block_1_expand_relu", "block_3_expand_relu",
                  "block_6_expand_relu", "block_13_expand_relu"]
    skips = [base.get_layer(n).output for n in skip_names]
    bottleneck = base.get_layer("block_16_project").output

    def up(x, f):
        x = layers.Conv2DTranspose(f, 3, strides=2, padding="same")(x)
        x = layers.BatchNormalization()(x)
        return layers.ReLU()(x)

    x = bottleneck
    for f, skip in zip([512, 256, 128, 64], reversed(skips)):
        x = up(x, f)
        x = layers.Concatenate()([x, skip])
        x = layers.Conv2D(f, 3, padding="same", activation="relu")(x)
    x = up(x, 32)
    outputs = layers.Conv2D(1, 1, activation="sigmoid")(x)
    return tf.keras.Model(inputs, outputs, name="lesion_unet")


def dice_bce_loss():
    import tensorflow as tf
    bce = tf.keras.losses.BinaryCrossentropy()
    def loss(y_true, y_pred):
        smooth = 1.0
        yt = tf.reshape(y_true, [-1]); yp = tf.reshape(y_pred, [-1])
        inter = tf.reduce_sum(yt * yp)
        dice = 1 - (2 * inter + smooth) / (tf.reduce_sum(yt) + tf.reduce_sum(yp) + smooth)
        return bce(y_true, y_pred) + dice
    return loss


def iou_metric():
    import tensorflow as tf
    def iou(y_true, y_pred):
        yp = tf.cast(y_pred > 0.5, tf.float32)
        inter = tf.reduce_sum(y_true * yp)
        union = tf.reduce_sum(tf.cast((y_true + yp) > 0, tf.float32))
        return (inter + 1e-6) / (union + 1e-6)
    return iou


def main():
    pip_install()
    download()
    jsons, img_dirs = probe()
    if PROBE_ONLY:
        print("\n[probe-only] exiting. Set PROBE_ONLY=0 to train.")
        return
    if not jsons or not img_dirs:
        raise SystemExit("Could not find COCO JSONs or images. Re-run with "
                         "PROBE_ONLY=1 and share the structure.")

    train_pairs, train_coco, kc = build_pairs(jsons, img_dirs, "train")
    val_pairs, val_coco, _ = build_pairs(jsons, img_dirs, "val")
    if not val_pairs:  # some releases only have train/test
        val_pairs, val_coco, _ = build_pairs(jsons, img_dirs, "test")
    if not train_pairs:
        raise SystemExit("No training pairs found. Re-run PROBE_ONLY=1 and share output.")

    os.makedirs(OUT_DIR, exist_ok=True)
    print("[data] materializing train...")
    tr = materialize(train_pairs, train_coco, kc, "/content/seg_data/train")
    print("[data] materializing val...")
    va = materialize(val_pairs, val_coco, kc, "/content/seg_data/val")

    import tensorflow as tf
    train_ds = make_ds(tr, True)
    val_ds = make_ds(va, False)

    model = build_unet()
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-4),
                  loss=dice_bce_loss(), metrics=[iou_metric()])
    ckpt = os.path.join(OUT_DIR, "lesion_segmenter.keras")
    cbs = [
        tf.keras.callbacks.ModelCheckpoint(ckpt, monitor="val_iou", mode="max", save_best_only=True),
        tf.keras.callbacks.EarlyStopping(monitor="val_iou", mode="max", patience=8, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-7),
    ]
    model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=cbs)
    model.save(ckpt)
    print(f"[ok] saved segmenter: {ckpt}")
    print("Download with:")
    print("  from google.colab import files")
    print(f"  files.download('{ckpt}')")


if __name__ == "__main__":
    main()
