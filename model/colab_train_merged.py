"""
ALL-IN-ONE Colab script: train ONE unified rice-disease classifier by MERGING
two datasets (Option 1):

  A) The Kaggle UCI paddy set  -> Bacterial leaf blight, Brown spot, Leaf smut
  B) An open HuggingFace set    -> more diseases + a HEALTHY class

Overlapping diseases (e.g. "Brown spot" in both) are merged into a single class.
Distinct diseases are kept separate. The result is one EfficientNetV2-B0 model
covering the UNION of all diseases plus Healthy - fixing both problems:
  * healthy leaves now classify as Healthy (no false disease)
  * you keep every disease from the original model AND gain new ones

------------------------------------------------------------------------------
CREDENTIALS: dataset A (Kaggle) needs your Kaggle token. Set it first:
    import os
    os.environ["KAGGLE_API_TOKEN"] = "KGAT_...your token..."
Dataset B (HuggingFace) is open, no token needed.
------------------------------------------------------------------------------

USAGE in Colab (GPU). Paste this file into a cell via:
    %%writefile /content/train_merged.py
then run:
    !python /content/train_merged.py

Config via env vars (all optional):
    KAGGLE_DATASET    default badhon7432/paddyleafdiseaseuci
    HF_ZIP_URL        default LeafNet75 rename.zip (open)
    EPOCHS / FT_EPOCHS / BATCH / OUT_DIR
    PROBE_ONLY        "1" to only merge + print the class counts, then exit
                      (do this FIRST to confirm the merged classes look right)
"""

import glob
import os
import re
import shutil
import subprocess
import sys
from collections import Counter


KAGGLE_DATASET = os.environ.get("KAGGLE_DATASET", "badhon7432/paddyleafdiseaseuci")
HF_ZIP_URL = os.environ.get(
    "HF_ZIP_URL",
    "https://huggingface.co/datasets/LeafNet75/Rice-Disease-Classification-Dataset/resolve/main/rename.zip",
)
RAW_A = "/content/merge_src/kaggle"
RAW_B = "/content/merge_src/hf"
MERGED = "/content/merged_dataset"
OUT_DIR = os.environ.get("OUT_DIR", "/content/merged_outputs")
IMG_SIZE = 224
EPOCHS = int(os.environ.get("EPOCHS", "25"))
FT_EPOCHS = int(os.environ.get("FT_EPOCHS", "12"))
BATCH = int(os.environ.get("BATCH", "32"))
PROBE_ONLY = os.environ.get("PROBE_ONLY", "0") == "1"

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp")

# Canonical class mapping. Any source folder name is normalized (lowercased,
# non-alphanumerics stripped) and matched here so equivalent diseases from the
# two datasets land in the SAME merged class. Unknown folders are kept using a
# cleaned version of their own name (so nothing is silently lost).
CANONICAL = {
    # healthy
    "healthy": "Healthy", "healthyleaf": "Healthy", "normal": "Healthy",
    "healthyriceleaf": "Healthy",
    # bacterial blight
    "bacterialblight": "Bacterial_Blight", "bacterialleafblight": "Bacterial_Blight",
    "blb": "Bacterial_Blight", "bacterialleafstreak": "Bacterial_Leaf_Streak",
    # brown spot
    "brownspot": "Brown_Spot", "brownspots": "Brown_Spot",
    # leaf smut
    "leafsmut": "Leaf_Smut", "smut": "Leaf_Smut", "falsesmut": "False_Smut",
    # blast
    "blast": "Blast", "leafblast": "Blast", "riceblast": "Blast",
    "neckblast": "Neck_Blast",
    # others commonly present
    "hispa": "Hispa", "tungro": "Tungro",
    "sheathblight": "Sheath_Blight", "bacterialpanicleblight": "Bacterial_Panicle_Blight",
}


def sh(cmd):
    print("+", cmd)
    subprocess.check_call(cmd, shell=True)


def pip_install():
    print("[setup] installing packages...")
    sh(f"{sys.executable} -m pip install -q -U tensorflow numpy pillow "
       f"matplotlib scikit-learn kaggle")


def _norm(name):
    n = name.lower()
    # Strip common crop prefixes so "Rice___Brown_Spot" == "Brown spot".
    n = re.sub(r"^(rice|paddy|oryza)[\s_\-]*", "", n)
    n = re.sub(r"[^a-z0-9]+", "", n)
    # Strip a trailing/leading 'rice' token too (some sets append it).
    if n.startswith("rice"):
        n = n[4:]
    return n


def canonical_name(folder):
    k = _norm(folder)
    if k in CANONICAL:
        return CANONICAL[k]
    # keep unknown classes under a Title_Case cleaned name (don't lose data)
    return re.sub(r"[^A-Za-z0-9]+", "_", folder).strip("_").title()


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
def download_kaggle():
    os.makedirs(RAW_A, exist_ok=True)
    if glob.glob(os.path.join(RAW_A, "**", "*.jpg"), recursive=True):
        print("[A] kaggle already present.")
        return
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if token:
        d = os.path.expanduser("~/.kaggle"); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "access_token"); open(p, "w").write(token); os.chmod(p, 0o600)
    print(f"[A] downloading Kaggle {KAGGLE_DATASET}")
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    api.dataset_download_files(KAGGLE_DATASET, path=RAW_A, unzip=True, quiet=False)
    print("[A] done.")


def download_hf():
    os.makedirs(RAW_B, exist_ok=True)
    if glob.glob(os.path.join(RAW_B, "**", "*.jpg"), recursive=True) or \
       glob.glob(os.path.join(RAW_B, "**", "*.png"), recursive=True):
        print("[B] hf already present.")
        return
    zp = os.path.join(RAW_B, "hf.zip")
    if not os.path.exists(zp) or os.path.getsize(zp) < 1_000_000:
        print(f"[B] downloading HF {HF_ZIP_URL}")
        sh(f'curl -L -C - -o "{zp}" "{HF_ZIP_URL}"')
    try:
        sh(f'unzip -q -o "{zp}" -d "{RAW_B}"')
    except subprocess.CalledProcessError:
        import zipfile
        with zipfile.ZipFile(zp) as z:
            z.extractall(RAW_B)
    print("[B] done.")


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def find_class_dirs(root):
    """Return {source_folder_name: [image_paths]} for the class-folder parent."""
    best_parent, best_score = None, -1
    for dp, dirs, _ in os.walk(root):
        score = 0
        for d in dirs:
            p = os.path.join(dp, d)
            try:
                if any(f.lower().endswith(IMG_EXTS) for f in os.listdir(p)):
                    score += 1
            except OSError:
                pass
        if score > best_score:
            best_score, best_parent = score, dp
    result = {}
    if best_parent:
        for d in sorted(os.listdir(best_parent)):
            p = os.path.join(best_parent, d)
            if os.path.isdir(p):
                imgs = [os.path.join(p, f) for f in os.listdir(p)
                        if f.lower().endswith(IMG_EXTS)]
                if imgs:
                    result[d] = imgs
    return result


def merge():
    if os.path.exists(MERGED):
        shutil.rmtree(MERGED)
    os.makedirs(MERGED, exist_ok=True)

    mapping = []  # (source, canonical, count)
    total = Counter()
    for tag, root in [("A", RAW_A), ("B", RAW_B)]:
        classes = find_class_dirs(root)
        for src_folder, imgs in classes.items():
            canon = canonical_name(src_folder)
            dst = os.path.join(MERGED, canon)
            os.makedirs(dst, exist_ok=True)
            for i, ip in enumerate(imgs):
                ext = os.path.splitext(ip)[1].lower()
                shutil.copy2(ip, os.path.join(dst, f"{tag}_{canon}_{total[canon]+i:06d}{ext}"))
            mapping.append((f"{tag}:{src_folder}", canon, len(imgs)))
            total[canon] += len(imgs)

    print("\n=== MERGE MAP (source -> canonical) ===")
    for src, canon, n in mapping:
        print(f"  {src:35s} -> {canon:22s} ({n})")
    print("\n=== MERGED CLASS TOTALS ===")
    for canon, n in sorted(total.items()):
        print(f"  {canon:22s} {n}")
    print(f"\n[merge] {len(total)} classes, {sum(total.values())} images total")
    return sorted(total.keys())


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def evaluate(model, vds, names, out_dir):
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import confusion_matrix, classification_report
    except ImportError:
        return
    yt, yp = [], []
    for im, la in vds:
        pr = model.predict(im, verbose=0)
        yt.extend(np.argmax(la.numpy(), 1)); yp.extend(np.argmax(pr, 1))
    print("\n[val] classification report:")
    print(classification_report(yt, yp, target_names=names))
    cm = confusion_matrix(yt, yp); n = len(names)
    f, ax = plt.subplots(figsize=(7, 6)); ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=45, ha="right"); ax.set_yticklabels(names)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max()/2 else "black")
    f.tight_layout(); f.savefig(os.path.join(out_dir, "confusion_matrix.png"), dpi=150)
    print("[ok] confusion_matrix.png saved")


def train():
    import numpy as np
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import EfficientNetV2B0

    os.makedirs(OUT_DIR, exist_ok=True)
    tds = tf.keras.utils.image_dataset_from_directory(
        MERGED, validation_split=0.2, subset="training", seed=123,
        image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH, label_mode="categorical")
    vds = tf.keras.utils.image_dataset_from_directory(
        MERGED, validation_split=0.2, subset="validation", seed=123,
        image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH, label_mode="categorical")
    names = tds.class_names; n = len(names)
    print("[data] class order:", names)

    cnt = Counter()
    for _, y in tds.unbatch():
        cnt[int(np.argmax(y.numpy()))] += 1
    tot = sum(cnt.values())
    cw = {i: tot/(n*cnt.get(i, 1)) for i in range(n)}

    AT = tf.data.AUTOTUNE
    tds = tds.prefetch(AT); vds = vds.prefetch(AT)
    aug = tf.keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.2), layers.RandomZoom(0.2),
        layers.RandomContrast(0.2)], name="aug")
    base = EfficientNetV2B0(input_shape=(IMG_SIZE, IMG_SIZE, 3),
                            include_top=False, weights="imagenet")
    base.trainable = False
    inp = tf.keras.Input((IMG_SIZE, IMG_SIZE, 3))
    x = aug(inp); x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x); x = layers.Dropout(0.3)(x)
    out = layers.Dense(n, activation="softmax")(x)
    model = models.Model(inp, out)

    ckpt = os.path.join(OUT_DIR, "rice_disease_effnetv2b0.keras")
    cbs = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7),
        tf.keras.callbacks.ModelCheckpoint(ckpt, monitor="val_accuracy", save_best_only=True),
    ]
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="categorical_crossentropy", metrics=["accuracy"])
    print("\n[stage 1] head..."); model.fit(tds, validation_data=vds, epochs=EPOCHS, class_weight=cw, callbacks=cbs)

    base.trainable = True
    for l in base.layers[:-60]:
        l.trainable = False
    for l in base.layers:
        if isinstance(l, layers.BatchNormalization):
            l.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
                  loss="categorical_crossentropy", metrics=["accuracy"])
    print("\n[stage 2] fine-tune..."); model.fit(tds, validation_data=vds, epochs=FT_EPOCHS, class_weight=cw, callbacks=cbs)

    model.save(ckpt)
    with open(os.path.join(OUT_DIR, "class_names.txt"), "w") as f:
        f.write("\n".join(names))
    print(f"[ok] saved model: {ckpt}")
    print(f"[ok] class_names -> {names}")
    evaluate(model, vds, names, OUT_DIR)


def main():
    pip_install()
    download_kaggle()
    download_hf()
    classes = merge()
    if PROBE_ONLY:
        print("\n[probe-only] merged classes:", classes)
        print("Set PROBE_ONLY=0 to train.")
        return
    train()
    print("\n[done] outputs in", OUT_DIR)
    print("Download:")
    print("  from google.colab import files")
    print(f"  files.download('{OUT_DIR}/rice_disease_effnetv2b0.keras')")
    print(f"  files.download('{OUT_DIR}/class_names.txt')")
    print(f"  files.download('{OUT_DIR}/confusion_matrix.png')")


if __name__ == "__main__":
    main()
