"""Generate Review III presentation PPT."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "PaddyGuard_Review_III_v2.pptx")
os.makedirs(os.path.join(HERE, "results"), exist_ok=True)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Colors
BG = RGBColor(0x0A, 0x14, 0x10)
CARD = RGBColor(0x12, 0x22, 0x1B)
GREEN = RGBColor(0x35, 0xD0, 0x7F)
LIME = RGBColor(0xB6, 0xF3, 0x6B)
AMBER = RGBColor(0xFF, 0xB4, 0x43)
RED = RGBColor(0xFF, 0x5A, 0x5A)
WHITE = RGBColor(0xE8, 0xF5, 0xEC)
MUTED = RGBColor(0x8F, 0xB3, 0xA0)
DARK = RGBColor(0x06, 0x13, 0x0C)


def set_bg(slide):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG


def add_text(slide, left, top, width, height, text, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = align
    return txBox


def add_card(slide, left, top, width, height):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_bullet_card(slide, left, top, width, height, title, bullets, title_color=GREEN):
    add_card(slide, left, top, width, height)
    add_text(slide, left+0.3, top+0.2, width-0.6, 0.5, title, size=16, color=title_color, bold=True)
    y = top + 0.7
    for b in bullets:
        add_text(slide, left+0.3, y, width-0.6, 0.4, f"• {b}", size=13, color=WHITE)
        y += 0.38


def add_table(slide, left, top, rows_data, col_widths, header_color=GREEN):
    rows = len(rows_data)
    cols = len(rows_data[0])
    tbl_shape = slide.shapes.add_table(rows, cols, Inches(left), Inches(top),
                                        sum(Inches(w) for w in col_widths), Inches(rows * 0.45))
    tbl = tbl_shape.table
    for ci, w in enumerate(col_widths):
        tbl.columns[ci].width = Inches(w)
    for ri, row in enumerate(rows_data):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = str(val)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(12)
            p.font.name = "Calibri"
            if ri == 0:
                p.font.bold = True
                p.font.color.rgb = DARK
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_color
            else:
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = CARD
    return tbl_shape


# ============================================================
# SLIDE 1 — Title
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
set_bg(s)
add_text(s, 1, 1.5, 11, 1.2, "PaddyGuard", size=48, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
add_text(s, 1, 2.8, 11, 0.8, "Deep Learning-Based Rice Leaf Disease Detection\n& Variable-Rate Chemical Spraying System", size=22, color=WHITE, align=PP_ALIGN.CENTER)
add_text(s, 1, 4.2, 11, 0.5, "Review III — Panel Review", size=18, color=MUTED, align=PP_ALIGN.CENTER)
add_text(s, 1, 5.5, 11, 0.5, "Based on Tewari et al. (2020) methodology", size=14, color=MUTED, align=PP_ALIGN.CENTER)

# ============================================================
# SLIDE 2 — Problem Statement & Objective
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Problem Statement & Objective", size=30, color=GREEN, bold=True)
add_bullet_card(s, 0.5, 1.2, 6, 3.0, "Problem", [
    "20-40% of global crop yield lost to plant diseases",
    "Traditional uniform spraying wastes chemicals & harms environment",
    "Manual disease diagnosis is slow and subjective",
    "Existing systems lack real severity measurement",
])
add_bullet_card(s, 6.8, 1.2, 6, 3.0, "Our Solution", [
    "CNN classifier identifies the disease type (6 classes incl. Healthy)",
    "Trained segmentation model measures actual diseased area",
    "Disease-specific dosing: different diseases get different spray intensity",
    "Variable-rate spray: solenoid open time proportional to severity",
    "Interactive web demo for real-time diagnosis",
], title_color=LIME)

# ============================================================
# SLIDE 3 — System Architecture
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "System Architecture — Pipeline", size=30, color=GREEN, bold=True)

steps = [
    ("1. Upload", "User uploads\na leaf image", GREEN),
    ("2. Classify", "EfficientNetV2-B0\nidentifies disease", LIME),
    ("3. Segment", "U-Net detects\nlesion pixels", LIME),
    ("4. Severity", "diseased ÷ leaf\n= severity %", AMBER),
    ("5. Spray", "C_eff → solenoid\nopen time (t_s)", RED),
]
for i, (title, desc, color) in enumerate(steps):
    x = 0.5 + i * 2.55
    add_card(s, x, 1.5, 2.3, 2.2)
    add_text(s, x+0.15, 1.6, 2.0, 0.5, title, size=16, color=color, bold=True)
    add_text(s, x+0.15, 2.2, 2.0, 1.0, desc, size=13, color=WHITE)

add_text(s, 0.5, 4.2, 12, 1.5,
    "Key novelty: The CNN diagnoses WHICH disease; segmentation measures HOW MUCH.\n"
    "These are independent — the disease type then scales the spray dose via a per-disease factor.\n"
    "Interactive leaf tracing (MobileSAM / free-form polygon) isolates the main leaf from cluttered backgrounds.",
    size=14, color=MUTED)

# ============================================================
# SLIDE 4 — Modules Implemented
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Modules Implemented", size=30, color=GREEN, bold=True)

modules = [
    ["Module", "Method", "Status"],
    ["Disease Classifier", "EfficientNetV2-B0 (transfer learning)", "Trained & deployed"],
    ["Lesion Segmenter", "U-Net (MobileNetV2 encoder), Dice+BCE", "Trained & deployed"],
    ["Leaf Isolation", "MobileSAM + free-form lasso", "Deployed"],
    ["Severity Measurement", "diseased px ÷ leaf px × 100", "Deployed"],
    ["Disease-Specific Dosing", "Per-disease factor × base coefficient", "Deployed"],
    ["Variable-Rate Spray", "Standardized solenoid timing (0.5–3.0s)", "Deployed"],
    ["Confidence Gate", "Flag uncertain predictions (<70%)", "Deployed"],
    ["Web Demo (PaddyGuard)", "Flask + animated frontend (3 tabs)", "Deployed"],
]
add_table(s, 0.5, 1.2, modules, [2.8, 4.5, 2.0])

# ============================================================
# SLIDE 5 — Classifier Results (3-class)
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Classifier Results — 3-Class Model (UCI Dataset)", size=30, color=GREEN, bold=True)

add_text(s, 0.5, 1.1, 6, 0.5, "Held-out test set: 164 images the model never saw", size=14, color=MUTED)

data3 = [
    ["Class", "Precision", "Recall", "F1", "Support"],
    ["Bacterial leaf blight", "1.00", "1.00", "1.00", "55"],
    ["Brown spot", "0.86", "0.89", "0.87", "54"],
    ["Leaf smut", "0.89", "0.85", "0.87", "55"],
    ["Overall accuracy", "", "", "0.915", "164"],
]
add_table(s, 0.5, 1.7, data3, [2.2, 1.1, 1.0, 0.9, 1.0])

# embed 3-class confusion matrix on the right
cm3 = os.path.join(HERE, "results", "confusion_matrix.png")
if os.path.exists(cm3):
    s.shapes.add_picture(cm3, Inches(7.4), Inches(1.6), height=Inches(3.6))

add_text(s, 0.5, 4.7, 6.5, 1.5,
    "Bacterial leaf blight classified perfectly. The small error is\n"
    "Brown spot ↔ Leaf smut (visually similar tan lesions).\n"
    "91.5% on a fully held-out set shows the architecture works well\n"
    "when class data is sufficient.",
    size=13, color=MUTED)

# ============================================================
# SLIDE 6 — Classifier Results (6-class merged)
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Classifier Results — 6-Class Merged Model", size=30, color=GREEN, bold=True)

add_text(s, 0.5, 1.1, 8, 0.5, "Held-out validation: 815 images · 4 of 6 classes evaluated (HF dataset)", size=14, color=MUTED)

data6 = [
    ["Class", "Precision", "Recall", "F1", "Support"],
    ["Neck_Blast", "1.00", "1.00", "1.00", "206"],
    ["Healthy", "0.83", "0.88", "0.85", "288"],
    ["Brown_Spot", "0.73", "0.74", "0.73", "126"],
    ["Blast", "0.74", "0.67", "0.71", "195"],
    ["Overall accuracy", "", "", "0.838", "815"],
]
add_table(s, 0.5, 1.7, data6, [2.2, 1.1, 1.0, 0.9, 1.0])

# embed 6-class confusion matrix on the right
cm6 = os.path.join(HERE, "results", "confusion_matrix_merged.png")
if os.path.exists(cm6):
    s.shapes.add_picture(cm6, Inches(7.4), Inches(1.6), height=Inches(3.7))

add_text(s, 0.5, 4.9, 6.5, 1.5,
    "Neck blast: perfect (1.00) · Healthy: strong (0.85) — the spray/\n"
    "don't-spray decision is reliable. Blast vs Brown spot are the\n"
    "weaker pair (both tan lesions). Bacterial Blight & Leaf Smut\n"
    "(55 imgs each) — known data limitation.",
    size=13, color=MUTED)

# ============================================================
# SLIDE 7 — Segmenter Results
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Lesion Segmenter Results", size=30, color=GREEN, bold=True)

add_text(s, 0.5, 1.1, 8, 0.5, "Evaluated on PlantSeg validation set: 1,247 images with expert pixel masks", size=14, color=MUTED)

seg_data = [
    ["Metric", "Our U-Net", "PlantSeg Best (SegNext)", "PlantSeg DeepLabV3+"],
    ["Mean IoU", "0.4450", "0.4452", "0.2508–0.2718"],
    ["Mean Dice", "0.5641", "—", "—"],
]
add_table(s, 0.5, 1.7, seg_data, [2.5, 2.0, 3.0, 3.0])

add_text(s, 0.5, 3.3, 12, 2.5,
    "Our lightweight binary U-Net (MobileNetV2 encoder) achieves 0.445 IoU —\n"
    "on par with the PlantSeg paper's BEST baseline (SegNext-MSCAN-L at 0.4452 mIoU)\n"
    "while being far smaller and faster.\n\n"
    "Note: PlantSeg baselines are on 115-class multi-disease segmentation;\n"
    "our task is simpler (binary lesion vs not), but the comparison demonstrates\n"
    "competitive pixel-level disease detection on in-the-wild images.\n\n"
    "The trained model clearly outperforms the classical colour-threshold method\n"
    "on cluttered field photos.",
    size=14, color=MUTED)

# ============================================================
# SLIDE 8 — Severity & Spray Mapping
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Severity → Variable-Rate Spray Mapping", size=30, color=GREEN, bold=True)

spray_data = [
    ["Severity %", "Level", "Base C", "Bact. blight (×1.2)", "Brown spot (×1.0)", "Leaf smut (×0.8)", "Spray time"],
    ["0 (Healthy)", "Healthy", "0.00", "0.00", "0.00", "0.00", "0.00 s"],
    ["0.1 – 5", "Low", "0.30", "0.36", "0.30", "0.24", "~1.1–1.4 s"],
    ["5.1 – 20", "Medium", "0.55", "0.66", "0.55", "0.44", "~1.6–2.2 s"],
    ["> 20", "High", "0.80", "0.96", "0.80", "0.64", "~2.1–2.9 s"],
]
add_table(s, 0.3, 1.2, spray_data, [1.3, 1.0, 0.9, 2.0, 2.0, 2.0, 1.3])

add_text(s, 0.5, 3.8, 12, 2.0,
    "Equations (Tewari et al. 2020):\n"
    "  a = (C_eff × A) / (d × 10)  [mL/hill]     A=500 L/ha, d=25 hills/m²\n"
    "  t_s = t_min + C_eff × (t_max − t_min)       t_min=0.5s, t_max=3.0s\n\n"
    "Solenoid timing standardized to a real 0.5–3.0s valve window\n"
    "(UNL Extension G2302; Agriculture 2024, 14(3), 361).\n"
    "Disease-specific factors ensure the CNN's diagnosis genuinely affects the spray dose.",
    size=13, color=MUTED, font_name="Consolas")

# ============================================================
# SLIDE 9 — Robustness Features
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Robustness & Safety Features", size=30, color=GREEN, bold=True)

features = [
    ("Confidence Gate (70%)", "Sub-70% predictions flagged as 'uncertain' —\nstops the system from asserting shaky guesses.", AMBER),
    ("Severity Floor (1.5%)", "If diseased area < 1.5% of leaf, treated as Healthy →\nno spray. Eliminates false positives from stray specks.", GREEN),
    ("Graceful Fallbacks", "Trained segmenter → colour method; SAM → auto leaf mask.\nEvery component degrades gracefully if unavailable.", LIME),
    ("Interactive Leaf Tracing", "Free-form polygon drawn by user becomes the leaf mask.\nSolves the 'background counted as leaf' problem.", LIME),
]
for i, (title, desc, color) in enumerate(features):
    row = i // 2
    col = i % 2
    x = 0.5 + col * 6.3
    y = 1.2 + row * 2.8
    add_card(s, x, y, 5.9, 2.4)
    add_text(s, x+0.3, y+0.2, 5.3, 0.5, title, size=16, color=color, bold=True)
    add_text(s, x+0.3, y+0.8, 5.3, 1.2, desc, size=13, color=WHITE)

# ============================================================
# SLIDE 10 — Known Limitations & Future Work
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 0.5, 0.3, 12, 0.7, "Known Limitations & Future Work", size=30, color=GREEN, bold=True)

add_bullet_card(s, 0.5, 1.2, 6, 4.0, "Current Limitations", [
    "Bacterial Blight & Leaf Smut: only 55 training images each → weakest classes",
    "Blast vs Brown Spot confusion (visually similar tan lesions)",
    "Field-photo segmentation imperfect on very cluttered backgrounds",
    "Spray timing (0.5–3.0s) is a research-backed default, not hardware-calibrated",
    "PlantSeg segmenter evaluated at 0.445 IoU — strong but not pixel-perfect",
], title_color=AMBER)

add_bullet_card(s, 6.8, 1.2, 6, 4.0, "Future Work", [
    "Collect more balanced training data for weak classes (biggest accuracy lever)",
    "Higher input resolution (299/384 px) to distinguish similar lesions",
    "Larger backbone (EfficientNetV2-B2/B3) for better feature extraction",
    "Hardware calibration: measure actual pump/nozzle → tune spray timing",
    "Deploy on edge device (TFLite on Raspberry Pi / ESP32 for field use)",
], title_color=LIME)

# ============================================================
# SLIDE 11 — Live Demo
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 1, 1.5, 11, 1.0, "Live Demo", size=44, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
add_text(s, 1, 2.8, 11, 0.6, "python app/server.py → http://127.0.0.1:5000", size=20, color=WHITE, align=PP_ALIGN.CENTER, font_name="Consolas")
add_text(s, 1, 3.8, 11, 2.5,
    "1. Upload a rice leaf image (drag & drop)\n"
    "2. Auto-analysis: disease class + severity + spray decision\n"
    "3. Trace around the main leaf for precise isolation\n"
    "4. Watch: animated severity formulas → disease-specific dosing → spray hose animation\n"
    "5. History tab: browse all past analyses\n"
    "6. About tab: pipeline explanation",
    size=18, color=MUTED, align=PP_ALIGN.CENTER)

# ============================================================
# SLIDE 12 — Thank You
# ============================================================
s = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s)
add_text(s, 1, 2.0, 11, 1.0, "Thank You", size=48, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
add_text(s, 1, 3.5, 11, 0.6, "Questions?", size=28, color=WHITE, align=PP_ALIGN.CENTER)
add_text(s, 1, 5.0, 11, 0.8,
    "PaddyGuard · EfficientNetV2-B0 + U-Net Segmentation + MobileSAM\n"
    "Based on Tewari et al. (2020) methodology",
    size=14, color=MUTED, align=PP_ALIGN.CENTER)

# Save
prs.save(OUT)
print(f"[ok] saved: {OUT}")
