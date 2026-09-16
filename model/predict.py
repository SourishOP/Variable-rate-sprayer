"""
Single-image inference: upload one rice leaf photo -> disease + severity level.

Pipeline:
    1. Load the trained EfficientNetV2-B0 model and class_names.txt.
    2. Classify the image -> disease class + confidence.
    3. If diseased, MEASURE severity by segmentation (severity.py) -> % of leaf
       area that is diseased.
    4. Map severity % -> Healthy / Low / Medium / High.

Usage:
    python predict.py --image leaf.jpg
    python predict.py --image leaf.jpg --model rice_disease_effnetv2b0.keras
    python predict.py --image leaf.jpg --save_overlay overlay.png

Outputs a JSON object with disease_class, confidence, severity_percent,
category, category_code, reduction_coefficient.
"""

import argparse
import json
import os

import numpy as np

import severity as sev

IMG_SIZE = 224
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "rice_disease_effnetv2b0.keras")
DEFAULT_CLASSES = os.path.join(HERE, "class_names.txt")


def load_class_names(path):
    if os.path.exists(path):
        with open(path) as f:
            names = [ln.strip() for ln in f if ln.strip()]
        if names:
            return names
    print(f"[warn] {path} not found; using DEFAULT_CLASS_NAMES from severity.py")
    return list(sev.DEFAULT_CLASS_NAMES)


def load_image_for_model(image_path):
    """Load and preprocess an image for EfficientNetV2 inference.

    Returns (batched_tensor, pil_rgb_image). The PIL image (original, unscaled)
    is passed to the severity segmenter so it measures on real pixels.
    """
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet_v2 import preprocess_input
    from PIL import Image

    pil = Image.open(image_path).convert("RGB")
    resized = pil.resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(resized, dtype=np.float32)
    arr = preprocess_input(arr)
    batch = np.expand_dims(arr, axis=0)
    return batch, pil


def save_overlay(image_path, out_path):
    """Save a visualization: leaf outline + diseased pixels highlighted."""
    import cv2
    from PIL import Image

    pil = Image.open(image_path).convert("RGB")
    bgr = sev._to_bgr_uint8(pil)
    leaf = sev.segment_leaf_mask(bgr)
    diseased = sev.segment_disease_mask(bgr, leaf)

    overlay = bgr.copy()
    overlay[diseased] = (0, 0, 255)  # red for diseased pixels
    blended = cv2.addWeighted(bgr, 0.6, overlay, 0.4, 0)
    cv2.imwrite(out_path, blended)
    print(f"[ok] overlay saved: {out_path}")


def predict(image_path, model_path, classes_path):
    import tensorflow as tf

    class_names = load_class_names(classes_path)
    model = tf.keras.models.load_model(model_path)

    batch, pil = load_image_for_model(image_path)
    probs = model.predict(batch, verbose=0)[0]

    # Combine classification with segmentation-based severity (pass the image).
    pred = sev.build_prediction(class_names, probs, image=pil)
    return pred


def main():
    parser = argparse.ArgumentParser(description="Predict rice disease + severity for one image.")
    parser.add_argument("--image", required=True, help="Path to the leaf image.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Path to trained .keras model.")
    parser.add_argument("--classes", default=DEFAULT_CLASSES, help="Path to class_names.txt.")
    parser.add_argument("--save_overlay", default=None, help="Optional path to save a diseased-area overlay image.")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        raise FileNotFoundError(f"Image not found: {args.image}")
    if not os.path.exists(args.model):
        raise FileNotFoundError(
            f"Model not found: {args.model}\n"
            "Train first with train_efficientnetv2.py or pass --model."
        )

    pred = predict(args.image, args.model, args.classes)
    print(json.dumps(pred.to_dict(), indent=2))

    if args.save_overlay:
        save_overlay(args.image, args.save_overlay)


if __name__ == "__main__":
    main()
