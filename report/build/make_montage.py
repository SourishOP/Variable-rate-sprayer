"""Make a labelled montage of sample test images (3 per class)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_DIR = os.path.join(ROOT, "data", "sample_images")
OUT = os.path.join(ROOT, "report", "figures", "fig_samples_montage.png")

pick = int(sys.argv[1]) if len(sys.argv) > 1 else 3
order = [("Bacterial_Blight", "Bacterial blight"), ("Brown_Spot", "Brown spot"),
         ("leaf_smut", "Leaf smut"), ("Neck Blast", "Neck blast"), ("healthy", "Healthy")]
cell = 300
pad = 8
label_h = 26
try:
    font = ImageFont.truetype("arial.ttf", 17)
except OSError:
    font = ImageFont.load_default()

W = pad + (cell + pad) * pick
H = pad + (cell + label_h + pad) * len(order)
canvas = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(canvas)
for r, (folder, label) in enumerate(order):
    files = sorted(f for f in os.listdir(os.path.join(TEST_DIR, folder))
                   if f.lower().endswith((".jpg", ".jpeg", ".png")))
    # spread the picks across the folder instead of taking the first ones
    idx = [int(i * (len(files) - 1) / max(1, pick - 1)) for i in range(pick)]
    y = pad + r * (cell + label_h + pad)
    draw.text((pad, y), label, fill=(20, 20, 20), font=font)
    for c, i in enumerate(idx):
        im = Image.open(os.path.join(TEST_DIR, folder, files[i])).convert("RGB")
        im.thumbnail((cell, cell))
        x = pad + c * (cell + pad)
        canvas.paste(im, (x + (cell - im.width) // 2, y + label_h + (cell - im.height) // 2))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
canvas.save(OUT)
print("saved", OUT, canvas.size)
