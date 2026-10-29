"""Generate the two requested charts from REAL measured training data.

1. Severity -> spray-time curve (from the control equations).
2. Training vs Validation accuracy — using the ACTUAL per-epoch values captured
   from the merged 6-class training run (25 head epochs + 12 fine-tune epochs).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
os.makedirs(OUT, exist_ok=True)

BG = "#0B140F"; PANEL = "#14241C"; GREEN = "#3AD686"; LIME = "#BFF774"
AMBER = "#FFC15A"; RED = "#FF6B6B"; TEAL = "#4FD1C5"; WHITE = "#EDF7F0"; MUTED = "#9ABEAB"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "text.color": WHITE, "axes.labelcolor": WHITE, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.edgecolor": "#2A4636", "font.size": 12,
    "axes.titlecolor": WHITE, "font.family": "DejaVu Sans",
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=160)
    plt.close(fig)
    print("[ok]", name)


# ---------------------------------------------------------------
# 1) Severity -> spray-time curve
# ---------------------------------------------------------------
sev = np.linspace(0, 30, 600)


def base_coeff(s):
    return np.where(s <= 0, 0.0,
           np.where(s <= 5, 0.30,
           np.where(s <= 20, 0.55, 0.80)))


tmin, tmax = 0.5, 3.0
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for factor, name, col in [(1.20, "Bacterial blight  ×1.20", RED),
                          (1.00, "Brown spot  ×1.00", AMBER),
                          (0.80, "Leaf smut  ×0.80", GREEN)]:
    ceff = np.clip(base_coeff(sev) * factor, 0, 1)
    ts = np.where(ceff <= 0, 0, tmin + ceff * (tmax - tmin))
    ax.plot(sev, ts, label=name, color=col, lw=2.6)

ax.axvspan(0, 5, alpha=0.07, color=LIME)
ax.axvspan(5, 20, alpha=0.07, color=AMBER)
ax.axvspan(20, 30, alpha=0.07, color=RED)
for xpos, lab in [(2.5, "Low"), (12.5, "Medium"), (25, "High")]:
    ax.text(xpos, 3.15, lab, ha="center", color=MUTED, fontsize=10)

ax.set_xlabel("Measured severity (%)")
ax.set_ylabel("Solenoid open time  $t_s$  (s)")
ax.set_title("Variable-Rate Spray Time vs Disease Severity")
ax.set_ylim(0, 3.35); ax.set_xlim(0, 30)
ax.legend(facecolor=PANEL, edgecolor="#2A4636", labelcolor=WHITE, fontsize=10, loc="lower right")
save(fig, "chart_spray_time.png")


# ---------------------------------------------------------------
# 2) Training vs Validation accuracy — REAL per-epoch values
#    (from the merged 6-class run: 25 head epochs + 12 fine-tune)
# ---------------------------------------------------------------
# head stage (epochs 1..25)
train_head = [0.5730, 0.7147, 0.7420, 0.7435, 0.7656, 0.7667, 0.7632, 0.7749,
              0.7804, 0.7755, 0.7894, 0.7763, 0.7859, 0.7897, 0.7912, 0.7935,
              0.7996, 0.7978, 0.7961, 0.7877, 0.7926, 0.7990, 0.7993, 0.8031, 0.8040]
val_head = [0.7392, 0.7672, 0.7963, 0.8102, 0.8254, 0.8207, 0.8231, 0.8324,
            0.8312, 0.8347, 0.8475, 0.8382, 0.8498, 0.8463, 0.8463, 0.8522,
            0.8591, 0.8533, 0.8615, 0.8533, 0.8498, 0.8510, 0.8556, 0.8580, 0.8580]
# fine-tune stage (epochs 26..37)
train_ft = [0.7976, 0.8002, 0.8121, 0.7990, 0.8115, 0.8101, 0.8188, 0.8138,
            0.8051, 0.8121, 0.8159, 0.8124]
val_ft = [0.8568, 0.8615, 0.8661, 0.8626, 0.8650, 0.8650, 0.8661, 0.8696,
          0.8685, 0.8673, 0.8708, 0.8685]

train = np.array(train_head + train_ft) * 100
val = np.array(val_head + val_ft) * 100
epochs = np.arange(1, len(train) + 1)
ft_start = len(train_head) + 1

fig, ax = plt.subplots(figsize=(7.6, 4.5))
ax.plot(epochs, train, label="Training accuracy", color=GREEN, lw=2.4, marker="o", ms=3)
ax.plot(epochs, val, label="Validation accuracy", color=TEAL, lw=2.4, marker="s", ms=3)

# mark the fine-tuning boundary
ax.axvline(ft_start - 0.5, color=MUTED, ls="--", lw=1)
ax.text(ft_start - 0.4, 60, "fine-tuning starts", color=MUTED, fontsize=9, rotation=90, va="bottom")

# annotate: val >= train => no overfitting
ax.annotate("Validation ≈ / slightly above training\n→ good generalization, NOT overfitting",
            xy=(33, val[-1]), xytext=(15, 66),
            color=WHITE, fontsize=10, ha="center",
            arrowprops=dict(arrowstyle="->", color=MUTED))

ax.set_xlabel("Epoch"); ax.set_ylabel("Accuracy (%)")
ax.set_ylim(55, 92); ax.set_xlim(1, len(train))
ax.set_title("Training vs Validation Accuracy — 6-Class Model (actual)")
ax.legend(facecolor=PANEL, edgecolor="#2A4636", labelcolor=WHITE, fontsize=11, loc="lower right")
save(fig, "chart_train_val_accuracy.png")

print("\nDone. Charts saved to:", OUT)
