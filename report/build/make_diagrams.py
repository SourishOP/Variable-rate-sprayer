"""Draw every diagram needed by the final report using diagram_lib.py
(matplotlib shapes only, no external drawing tool). All diagrams are labelled
as diagrams in the report (not photographs).

Run with the doc-building venv:
  %LOCALAPPDATA%/final_report_work/venv/Scripts/python.exe make_diagrams.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from diagram_lib import Canvas, BLUE, RED, ORANGE, GREEN, GREY, BLACK, EDGE  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIG = os.path.join(ROOT, "report", "figures")
os.makedirs(FIG, exist_ok=True)


def out(name):
    return os.path.join(FIG, name)


# ---------------------------------------------------------------------------
# 1. System block diagram
# ---------------------------------------------------------------------------
def fig_block_diagram():
    c = Canvas(height_cm=13)
    c.box("cam", 2, 62, 20, 14, "ESP32-CAM\n(OV2640 camera,\nWiFi)", fill="blue")
    c.box("cloud", 28, 62, 24, 14, "Cloud inference API\n(Flask, EfficientNetV2-B0\n+ U-Net segmenter)", fill="teal")
    c.box("blynk", 58, 70, 20, 10, "Blynk IoT\ndashboard", fill="violet")
    c.box("blynk2", 58, 56, 20, 10, "Status LEDs\non ESP32-CAM", fill="violet")
    c.box("nano", 28, 38, 20, 14, "Arduino Nano\n(computes ts,\ndrives relay)", fill="amber")
    c.box("relay", 54, 38, 16, 14, "5V relay\nmodule", fill="amber")
    c.box("valve", 76, 38, 16, 14, "12V solenoid\nvalve (NC)", fill="rose")
    c.box("pump", 2, 38, 16, 14, "12V\npump", fill="rose")
    c.box("tank", 2, 18, 16, 14, "Chemical\ntank", fill="grey")
    c.box("nozzle", 76, 18, 16, 14, "Spray\nnozzle", fill="green")
    c.box("batt", 28, 18, 20, 14, "3 x 18650 battery\n+ LM2596 buck", fill="grey")

    c.arrow(c.anchor("cam", "r"), c.anchor("cloud", "l"))
    c.label(25, 71, "JPEG\n(HTTP POST)", fs=6.5)
    c.arrow(c.anchor("cloud", "r"), c.anchor("blynk", "l"), rad=0.15)
    c.arrow(c.anchor("cloud", "r"), c.anchor("blynk2", "l"), rad=-0.15)
    c.label(52, 68, "JSON result", fs=6.5)
    c.arrow(c.anchor("cloud", "b"), c.anchor("nano", "t"))
    c.label(44, 56, "category code\n(serial)", fs=6.5)
    c.arrow(c.anchor("nano", "r"), c.anchor("relay", "l"))
    c.arrow(c.anchor("relay", "r"), c.anchor("valve", "l"))
    c.arrow(c.anchor("pump", "r"), c.anchor("valve", "l"), rad=-0.25)
    c.arrow(c.anchor("tank", "t"), c.anchor("pump", "l"), rad=0.2)
    c.arrow(c.anchor("valve", "r"), c.anchor("nozzle", "l"))
    c.arrow(c.anchor("batt", "l"), c.anchor("pump", "r"), rad=-0.2, color=GREY, ls="--")
    c.arrow(c.anchor("batt", "t"), c.anchor("nano", "b"), color=GREY, ls="--")
    c.label(50, 14, "liquid path", fs=7, italic=True, color=GREY)
    c.label(20, 14, "power (12V / 5V)", fs=7, italic=True, color=GREY)
    c.save(out("fig_block_diagram.png"))


# ---------------------------------------------------------------------------
# 2. One spray-cycle flowchart
# ---------------------------------------------------------------------------
def fig_cycle_flowchart():
    c = Canvas(height_cm=20)
    ys = [94, 84, 74, 64, 54, 44, 34, 24, 12]
    c.ellipse("start", 50, ys[0], 24, 7, "Start / trigger", fill="green", bold=True)
    c.box("capture", 30, ys[1] - 3.5, 40, 7, "ESP32-CAM captures a 640x480 JPEG", fill="blue")
    c.box("send", 30, ys[2] - 3.5, 40, 7, "Image sent to the cloud API (HTTP POST)", fill="blue")
    c.box("classify", 30, ys[3] - 3.5, 40, 7, "EfficientNetV2-B0 predicts the disease class", fill="teal")
    c.box("segment", 30, ys[4] - 3.5, 40, 7, "U-Net measures the diseased leaf area (severity %)", fill="teal")
    c.diamond("guard", 50, ys[5], 42, 9, "Severity < 1.5% or\nconfidence < 70%?", fill="amber", fs=7)
    c.box("healthy", 68, ys[6] - 3.5, 26, 7, "Treated as Healthy,\nno spray", fill="green")
    c.box("dose", 20, ys[6] - 3.5, 36, 7, "Category -> C_eff,\nsolenoid time ts", fill="rose")
    c.box("spray", 20, ys[7] - 3.5, 36, 7, "Relay opens the solenoid for ts seconds", fill="rose")
    c.box("log", 30, ys[8] - 3.5, 40, 7, "Result pushed to Blynk dashboard and logged", fill="violet")
    c.ellipse("end", 50, 4, 24, 6, "End / wait for next trigger", fill="green", bold=True)

    def down(a, b):
        c.arrow(c.anchor(a, "b"), c.anchor(b, "t"))

    down("start", "capture")
    down("capture", "send")
    down("send", "classify")
    down("classify", "segment")
    c.arrow(c.anchor("segment", "b"), c.anchor("guard", "t"))
    c.arrow(c.anchor("guard", "r"), c.anchor("healthy", "t"))
    c.label(72, ys[5] - 2, "yes", fs=7)
    c.arrow(c.anchor("guard", "l"), c.anchor("dose", "t"))
    c.label(27, ys[5] - 2, "no", fs=7)
    c.arrow(c.anchor("dose", "b"), c.anchor("spray", "t"))
    c.arrow(c.anchor("healthy", "b"), c.anchor("log", "t"), rad=-0.2)
    c.arrow(c.anchor("spray", "b"), c.anchor("log", "t"), rad=0.1)
    c.arrow(c.anchor("log", "b"), c.anchor("end", "t"))
    c.save(out("fig_cycle_flowchart.png"))


# ---------------------------------------------------------------------------
# 3. Layered architecture
# ---------------------------------------------------------------------------
def fig_layered_architecture():
    c = Canvas(height_cm=15)
    layers = [
        ("Perception layer", "ESP32-CAM image capture, WiFi upload", "blue", 82),
        ("Intelligence layer", "EfficientNetV2-B0 classifier, U-Net lesion segmenter,\nseverity and dose calculation (cloud Flask API)", "teal", 61),
        ("Decision and control layer", "Arduino Nano: category to coefficient to solenoid time,\nrelay control, safety time cap", "amber", 40),
        ("Actuation layer", "Relay, 12V solenoid valve, pump, nozzle, liquid path", "rose", 19),
        ("Monitoring layer", "Blynk IoT dashboard, status LEDs, history log", "violet", 2),
    ]
    for name, desc, fill, y in layers:
        c.box(name, 4, y, 92, 15, "", fill=fill)
        c.label(8, y + 11, name, fs=9.5, bold=True, ha="left")
        c.label(8, y + 5, desc, fs=7.8, ha="left")
    for i in range(len(layers) - 1):
        y1 = layers[i][3]
        c.arrow((50, y1), (50, y1 - 2), color=GREY)
    c.save(out("fig_layered_architecture.png"))


# ---------------------------------------------------------------------------
# 4. Class distribution (real training counts, merged 6-class dataset)
# ---------------------------------------------------------------------------
def fig_class_distribution():
    classes = ["Healthy", "Blast", "Neck_Blast", "Brown_Spot", "Bacterial_Blight", "Leaf_Smut"]
    counts = [1488, 977, 1000, 667, 55, 55]
    colors = ["#2E7D32", "#D2780B", "#C0392B", "#8A6D3B", "#1F5FAA", "#6B7785"]
    fig, ax = plt.subplots(figsize=(14.65 / 2.54, 8 / 2.54))
    bars = ax.bar(classes, counts, color=colors)
    for b, v in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, v + 20, str(v), ha="center", fontsize=9)
    ax.set_ylabel("Training images")
    ax.set_title("Merged 6-class dataset: training image count per class (total 4,242)")
    ax.spines[["top", "right"]].set_visible(False)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(out("fig_class_distribution.png"), dpi=220)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. Classifier architecture (transfer learning)
# ---------------------------------------------------------------------------
def fig_classifier_architecture():
    c = Canvas(height_cm=9)
    c.box("in", 2, 36, 14, 16, "Input\n224x224x3\nRGB leaf image", fill="grey", fs=7)
    c.box("aug", 18, 36, 13, 16, "Data\naugmentation\n(flip, rotate,\nbrightness)", fill="grey", fs=6.8)
    c.box("base", 33, 32, 30, 24, "EfficientNetV2-B0 backbone\n(ImageNet pretrained)\nfrozen, then fine tuned\nin stage 2", fill="blue", fs=7.2)
    c.box("pool", 65, 36, 13, 16, "Global\naverage\npooling", fill="teal", fs=7)
    c.box("head", 80, 36, 16, 16, "Dense + softmax\n6 classes", fill="amber", fs=7)
    for a, b in [("in", "aug"), ("aug", "base"), ("base", "pool"), ("pool", "head")]:
        c.arrow(c.anchor(a, "r"), c.anchor(b, "l"))
    c.label(50, 14, "Stage 1: train the head with the backbone frozen (25 epochs).\n"
                     "Stage 2: unfreeze and fine tune the whole network at a lower learning rate (12 epochs).",
            fs=7.5, bg=True)
    c.save(out("fig_classifier_architecture.png"))


# ---------------------------------------------------------------------------
# 6. Severity pipeline
# ---------------------------------------------------------------------------
def fig_severity_pipeline():
    c = Canvas(height_cm=9)
    c.box("img", 2, 34, 16, 18, "Leaf image", fill="grey", fs=7.5)
    c.box("leaf", 22, 34, 20, 18, "Leaf mask\n(colour threshold,\nSAM, or traced\noutline)", fill="green", fs=7)
    c.box("lesion", 46, 34, 20, 18, "Lesion mask\n(trained U-Net,\nor colour fallback)", fill="rose", fs=7)
    c.box("ratio", 70, 34, 26, 18,
          "Severity % =\n100 x diseased px / leaf px", fill="amber", fs=7.5)
    for a, b in [("img", "leaf"), ("leaf", "lesion"), ("lesion", "ratio")]:
        c.arrow(c.anchor(a, "r"), c.anchor(b, "l"))
    c.label(50, 10, "Both masks come from the same image; the ratio of their pixel counts gives severity.",
            fs=7.5, bg=True)
    c.save(out("fig_severity_pipeline.png"))


# ---------------------------------------------------------------------------
# 7. Circuit / wiring diagram
# ---------------------------------------------------------------------------
def fig_circuit_wiring():
    c = Canvas(height_cm=14)
    c.box("esp", 4, 70, 22, 16, "ESP32-CAM\nGPIO1(TX)  GPIO13  GPIO12,2,14,15\n5V   GND", fill="blue", fs=7)
    c.box("nano", 38, 70, 22, 16, "Arduino Nano\nD10(RX) D7  D13\n5V   GND", fill="amber", fs=7)
    c.box("relay", 72, 70, 22, 16, "Relay module\nVCC IN GND\nCOM  NO  NC", fill="rose", fs=7)
    c.box("buck", 4, 44, 22, 14, "LM2596 buck\nVIN+/- -> 5V out", fill="grey", fs=7)
    c.box("batt", 38, 44, 22, 14, "3 x 18650\n(~11.1-12.6V)\n+ 2A fuse", fill="grey", fs=7)
    c.box("solenoid", 72, 44, 22, 14, "12V solenoid\nvalve (NC)", fill="teal", fs=7)
    c.box("button", 4, 24, 16, 12, "Push\nbutton\n(GPIO13)", fill="violet", fs=7)
    c.box("leds", 24, 24, 20, 12, "4 status LEDs\n(220 ohm each)", fill="violet", fs=7)
    c.box("pump", 72, 24, 22, 12, "12V pump\n(wired direct,\nno switch)", fill="teal", fs=7)

    c.arrow(c.anchor("esp", "r"), c.anchor("nano", "l"))
    c.label(35, 80, "GPIO1 -> D10\n(serial, 9600 baud)", fs=6.3)
    c.arrow(c.anchor("nano", "r"), c.anchor("relay", "l"))
    c.label(69, 80, "D7 -> IN", fs=6.3)
    c.arrow(c.anchor("relay", "b"), c.anchor("solenoid", "t"))
    c.label(85, 60, "NO -> (+)", fs=6.3)
    c.arrow(c.anchor("batt", "r"), c.anchor("relay", "l"), rad=0.3)
    c.label(60, 60, "COM (12V, via fuse)", fs=6.3)
    c.arrow(c.anchor("batt", "l"), c.anchor("buck", "r"))
    c.arrow(c.anchor("buck", "t"), c.anchor("esp", "b"), rad=0.2)
    c.arrow(c.anchor("buck", "t"), c.anchor("nano", "b"), rad=0.1)
    c.arrow(c.anchor("buck", "t"), c.anchor("relay", "b"), rad=0.35, color=GREY)
    c.label(16, 58, "5V to all three boards", fs=6.3)
    c.arrow(c.anchor("esp", "b"), c.anchor("button", "t"), rad=-0.1)
    c.arrow(c.anchor("esp", "b"), c.anchor("leds", "t"), rad=0.1)
    c.arrow(c.anchor("batt", "r"), c.anchor("pump", "l"), rad=-0.3)
    c.label(50, 10, "Dashed power lines are omitted for clarity; all boards share one common ground.",
            fs=7.2, italic=True, color=GREY)
    c.save(out("fig_circuit_wiring.png"))


# ---------------------------------------------------------------------------
# 8. Power distribution diagram
# ---------------------------------------------------------------------------
def fig_power_distribution():
    c = Canvas(height_cm=14)
    c.box("batt", 4, 60, 24, 20, "3 x 18650 Li-ion\n(11.1-12.6V)\n2600 mAh", fill="grey", fs=7.5)
    c.box("fuse", 32, 65, 12, 10, "2A\nfuse", fill="amber", fs=7)
    c.box("buck", 48, 60, 20, 20, "LM2596\nbuck converter\n(5.00V set point)", fill="teal", fs=7.5)
    c.box("espP", 72, 76, 22, 10, "ESP32-CAM\n~300 mA", fill="blue", fs=7)
    c.box("nanoP", 72, 62, 22, 10, "Arduino Nano\n~50 mA", fill="blue", fs=7)
    c.box("relayP", 72, 48, 22, 10, "Relay module\n~70 mA", fill="blue", fs=7)
    c.box("pumpP", 4, 20, 22, 14, "Pump (12V)\n~500 mA\ncontinuous", fill="rose", fs=7)
    c.box("solP", 30, 20, 22, 14, "Solenoid (12V)\n~300 mA\nwhile open", fill="rose", fs=7)
    c.arrow(c.anchor("batt", "r"), c.anchor("fuse", "l"))
    c.arrow(c.anchor("fuse", "r"), c.anchor("buck", "l"))
    for name in ("espP", "nanoP", "relayP"):
        c.arrow(c.anchor("buck", "r"), c.anchor(name, "l"), rad=(0.2 if name == "espP" else (-0.2 if name == "relayP" else 0)))
    c.arrow(c.anchor("batt", "b"), c.anchor("pumpP", "t"), rad=-0.1)
    c.arrow(c.anchor("batt", "b"), c.anchor("solP", "t"), rad=0.15)
    c.label(50, 10, "Total approx. 1.2 A at 12V; a 2600 mAh pack gives roughly 2 hours of continuous operation.",
            fs=7.5, bg=True)
    c.save(out("fig_power_distribution.png"))


# ---------------------------------------------------------------------------
# 9. Liquid path diagram
# ---------------------------------------------------------------------------
def fig_liquid_path():
    c = Canvas(height_cm=8)
    c.box("tank", 4, 28, 18, 24, "Chemical\ntank", fill="grey", fs=8)
    c.box("pump", 28, 28, 18, 24, "R385\npump", fill="rose", fs=8)
    c.box("valve", 52, 28, 18, 24, "Solenoid\nvalve (NC)\nopens for ts", fill="amber", fs=7.5)
    c.box("nozzle", 76, 28, 18, 24, "Hollow cone\nnozzle", fill="green", fs=8)
    for a, b in [("tank", "pump"), ("pump", "valve"), ("valve", "nozzle")]:
        c.arrow(c.anchor(a, "r"), c.anchor(b, "l"))
    c.label(50, 12, "6 mm silicone tubing connects every stage; the pump runs continuously\n"
                     "and the solenoid, not the pump, meters the dose.", fs=7.3, bg=True)
    c.save(out("fig_liquid_path.png"))


# ---------------------------------------------------------------------------
# 10. DFD level 0 (context diagram)
# ---------------------------------------------------------------------------
def fig_dfd_level0():
    c = Canvas(height_cm=11)
    c.ellipse("sys", 50, 50, 44, 26, "0\nVariable rate paddy\nspraying system", fill="blue", bold=True, fs=9)
    c.box("farmer", 4, 58, 18, 14, "Farmer /\noperator", fill="grey", fs=8)
    c.box("field", 4, 24, 18, 14, "Paddy\nfield", fill="green", fs=8)
    c.box("app", 78, 58, 18, 14, "Blynk\ndashboard", fill="violet", fs=8)
    c.arrow(c.anchor("farmer", "r"), c.anchor("sys", "l"), rad=0.1)
    c.label(30, 68, "trigger", fs=7)
    c.arrow(c.anchor("field", "r"), c.anchor("sys", "l"), rad=-0.1)
    c.label(30, 32, "leaf image", fs=7)
    c.arrow(c.anchor("sys", "r"), c.anchor("app", "l"))
    c.label(70, 68, "severity, usage", fs=7)
    c.arrow(c.anchor("sys", "b"), c.anchor("field", "t"), rad=-0.3)
    c.label(45, 20, "measured spray", fs=7)
    c.save(out("fig_dfd_level0.png"))


# ---------------------------------------------------------------------------
# 11. DFD level 1
# ---------------------------------------------------------------------------
def fig_dfd_level1():
    c = Canvas(height_cm=15)
    c.box("farmer", 2, 80, 16, 12, "Farmer", fill="grey", fs=7.5)
    c.ellipse("p1", 30, 83, 22, 13, "1\nCapture\nimage", fill="blue", fs=7.5)
    c.ellipse("p2", 58, 83, 22, 13, "2\nClassify\ndisease", fill="teal", fs=7.5)
    c.ellipse("p3", 58, 60, 22, 13, "3\nMeasure\nseverity", fill="teal", fs=7.5)
    c.ellipse("p4", 30, 60, 22, 13, "4\nCompute dose\nand ts", fill="amber", fs=7.5)
    c.ellipse("p5", 30, 37, 22, 13, "5\nActuate\nsolenoid", fill="rose", fs=7.5)
    c.ellipse("p6", 58, 37, 22, 13, "6\nLog and\ndisplay", fill="violet", fs=7.5)
    c.box("d1", 2, 54, 16, 10, "D1 class\nnames", fill="grey", fs=6.8)
    c.box("d2", 2, 30, 16, 10, "D2 history\nlog", fill="grey", fs=6.8)
    c.box("field", 84, 60, 14, 12, "Paddy\nplant", fill="green", fs=7.2)
    c.box("app2", 84, 37, 14, 12, "Blynk\napp", fill="violet", fs=7.2)

    c.arrow(c.anchor("farmer", "r"), c.anchor("p1", "l"))
    c.arrow(c.anchor("p1", "r"), c.anchor("p2", "l"))
    c.arrow(c.anchor("p2", "b"), c.anchor("p3", "t"))
    c.arrow(c.anchor("d1", "r"), c.anchor("p2", "l"), rad=0.2, color=GREY, ls="--")
    c.arrow(c.anchor("p3", "l"), c.anchor("p4", "r"))
    c.arrow(c.anchor("p4", "b"), c.anchor("p5", "t"))
    c.arrow(c.anchor("p5", "r"), c.anchor("p6", "l"))
    c.arrow(c.anchor("p6", "r"), c.anchor("app2", "l"), rad=-0.1)
    c.arrow(c.anchor("p6", "b"), c.anchor("d2", "l"), rad=-0.3, color=GREY, ls="--")
    c.arrow(c.anchor("field", "l"), c.anchor("p3", "r"), rad=0.1)
    c.save(out("fig_dfd_level1.png"))


# ---------------------------------------------------------------------------
# 12. Use case diagram
# ---------------------------------------------------------------------------
def fig_use_case():
    c = Canvas(height_cm=16)
    c.label(16, 95, "Farmer", fs=9, bold=True)
    c.ax.plot([16, 16], [91, 75], color=EDGE, lw=1.2)
    c.ax.plot([10, 22], [83, 83], color=EDGE, lw=1.2)
    c.ax.plot([16, 10], [75, 67], color=EDGE, lw=1.2)
    c.ax.plot([16, 22], [75, 67], color=EDGE, lw=1.2)
    c.region(32, 8, 62, 82, "")
    uses = [
        ("u1", "Trigger a capture", 78),
        ("u2", "View diagnosis\nand severity", 64),
        ("u3", "Trigger a\nspray cycle", 50),
        ("u4", "View usage history\non Blynk", 36),
        ("u5", "Upload a leaf photo\n(web demo)", 22),
        ("u6", "Trace the leaf\noutline (web demo)", 10),
    ]
    for name, text, y in uses:
        c.ellipse(name, 62, y, 30, 11, text, fill="blue", fs=7.2)
        c.arrow((22, 75), c.anchor(name, "l"), rad=0.05)
    c.save(out("fig_use_case.png"))


# ---------------------------------------------------------------------------
# 13. Sequence diagram
# ---------------------------------------------------------------------------
def fig_sequence():
    c = Canvas(height_cm=15)
    actors = [("Farmer", 7), ("ESP32-CAM", 24), ("Cloud API", 41), ("Arduino Nano", 58), ("Relay+Valve", 75), ("Blynk", 92)]
    top = 90
    for name, x in actors:
        c.box(name, x - 8, top, 16, 7, name, fill="grey", fs=6.6)
        c.ax.plot([x, x], [top, 4], color=GREY, lw=0.8, ls=":")

    steps = [
        (7, 24, 82, "press trigger"),
        (24, 41, 76, "POST image"),
        (41, 41, 70, "classify + segment"),
        (41, 24, 64, "JSON result"),
        (24, 58, 58, "category code (serial)"),
        (58, 58, 52, "compute ts"),
        (58, 75, 46, "relay ON for ts"),
        (75, 75, 40, "spray"),
        (24, 92, 34, "push severity, usage"),
        (92, 7, 28, "show on dashboard"),
    ]
    for x1, x2, y, text in steps:
        if x1 == x2:
            c.ax.add_patch(plt.Rectangle((x1 - 1, y - 2), 2, 4, fc="white", ec=EDGE, lw=0.8))
            c.label(x1, y, "", fs=1)
            c.label(x1 + 10, y, text, fs=6.3, ha="left")
        else:
            c.arrow((x1, y), (x2, y), lw=0.9)
            c.label((x1 + x2) / 2, y + 2.3, text, fs=6.3)
    c.save(out("fig_sequence.png"))


# ---------------------------------------------------------------------------
# 14. Module / class diagram (software)
# ---------------------------------------------------------------------------
def fig_module_diagram():
    c = Canvas(height_cm=12)
    c.box("server", 4, 62, 30, 18,
          "server.py (Flask)\n+ /predict()\n+ /health()\n+ index()", fill="blue", fs=7)
    c.box("severity", 40, 62, 30, 18,
          "severity.py\n+ measure_severity()\n+ build_prediction_*()\n+ spray_time()", fill="teal", fs=7)
    c.box("model", 76, 62, 20, 18,
          "Trained models\nEfficientNetV2-B0\nU-Net, MobileSAM", fill="amber", fs=7)
    c.box("web", 4, 36, 30, 18,
          "static/index.html\n(upload UI, mask view,\nspray animation)", fill="violet", fs=7)
    c.box("predict", 40, 36, 30, 18,
          "predict.py\n(CLI single-image\ninference)", fill="green", fs=7)
    c.box("train", 76, 36, 20, 18,
          "colab_train_*.py\n(training scripts)", fill="rose", fs=7)
    c.arrow(c.anchor("web", "t"), c.anchor("server", "b"))
    c.arrow(c.anchor("server", "r"), c.anchor("severity", "l"))
    c.arrow(c.anchor("severity", "r"), c.anchor("model", "l"))
    c.arrow(c.anchor("predict", "t"), c.anchor("severity", "b"))
    c.arrow(c.anchor("train", "l"), c.anchor("model", "b"), rad=0.2)
    c.save(out("fig_module_diagram.png"))


# ---------------------------------------------------------------------------
# 15. Gantt chart (14 weeks, from the review 2 deck feasibility slide)
# ---------------------------------------------------------------------------
def fig_gantt():
    tasks = [
        ("Literature review, problem definition, Review 1", 1, 2, "Both"),
        ("CNN model training and validation", 3, 2, "Sourish"),
        ("Flask API and ngrok, Review 2 prep", 5, 2, "Sourish"),
        ("ESP32-CAM firmware (capture + HTTP)", 7, 2, "Aditya"),
        ("Arduino code and hardware assembly, Review 3", 9, 2, "Aditya"),
        ("Blynk IoT and field testing, VRA vs CRA comparison", 11, 2, "Both"),
        ("Results analysis and report, Review 4", 13, 1, "Both"),
        ("Final demo and viva, Review 5", 14, 1, "Both"),
    ]
    colors = {"Sourish": "#1F5FAA", "Aditya": "#D2780B", "Both": "#2E7D32"}
    fig, ax = plt.subplots(figsize=(14.65 / 2.54, 9 / 2.54))
    for i, (name, start, dur, owner) in enumerate(tasks):
        y = len(tasks) - i
        ax.barh(y, dur, left=start, height=0.55, color=colors[owner], edgecolor="black", linewidth=0.5)
        ax.text(start + dur + 0.15, y, name, va="center", fontsize=7.6)
    ax.set_yticks([])
    ax.set_xlim(1, 30)
    ax.set_ylim(0, len(tasks) + 2.2)
    ax.set_xticks(range(1, 15))
    ax.set_xlabel("Project week")
    ax.set_title("Project schedule (14 weeks)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in colors.values()]
    ax.legend(handles, colors.keys(), loc="upper right", fontsize=8, title="Owner")
    fig.tight_layout()
    fig.savefig(out("fig_gantt.png"), dpi=220)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 16. Chemical usage comparison chart
# ---------------------------------------------------------------------------
def fig_chemical_comparison():
    labels = ["Base paper\n(Tewari et al., 2020)\nCRA vs VRA field trial",
              "This project\nequation dose\n(49 test images, simulation)",
              "This project\nvalve open volume\n(49 test images, simulation)"]
    savings = [33.88, 43.2, 40.08]
    fig, ax = plt.subplots(figsize=(14.65 / 2.54, 8 / 2.54))
    bars = ax.bar(labels, savings, color=["#6B7785", "#1F5FAA", "#2E7D32"])
    for b, v in zip(bars, savings):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontsize=9.5)
    ax.set_ylabel("Chemical saved vs constant full rate (%)")
    ax.set_ylim(0, 55)
    ax.set_title("Chemical saving: base paper field trial vs this project's software simulation")
    ax.spines[["top", "right"]].set_visible(False)
    plt.setp(ax.get_xticklabels(), fontsize=8)
    fig.tight_layout()
    fig.savefig(out("fig_chemical_comparison.png"), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    fig_block_diagram()
    fig_cycle_flowchart()
    fig_layered_architecture()
    fig_class_distribution()
    fig_classifier_architecture()
    fig_severity_pipeline()
    fig_circuit_wiring()
    fig_power_distribution()
    fig_liquid_path()
    fig_dfd_level0()
    fig_dfd_level1()
    fig_use_case()
    fig_sequence()
    fig_module_diagram()
    fig_gantt()
    fig_chemical_comparison()
    print("All diagrams written to", FIG)
