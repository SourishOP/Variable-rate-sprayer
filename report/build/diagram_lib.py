"""Small drawing helper for the report diagrams (matplotlib only).

Every diagram is drawn on a 100-unit-wide canvas that maps to the 14.65 cm text
width of the report, so font sizes in points are the real printed sizes.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon


def _pick_font():
    names = {f.name for f in fm.fontManager.ttflist}
    for cand in ("Arial", "Calibri", "Segoe UI", "DejaVu Sans"):
        if cand in names:
            return cand
    return "DejaVu Sans"


FONT = _pick_font()
plt.rcParams["font.family"] = FONT
plt.rcParams["axes.unicode_minus"] = False

FILL = {
    "blue": "#DCE9F7", "green": "#DDEFDD", "amber": "#FBEFC9", "rose": "#F7DCDC",
    "violet": "#E8DFF3", "grey": "#EDEDED", "teal": "#D6EEEC", "white": "#FFFFFF",
}
EDGE = "#2B3A4A"
BLACK = "#1A1A1A"
RED = "#C0392B"
BLUE = "#1F5FAA"
ORANGE = "#D2780B"
GREEN = "#2E7D32"
GREY = "#6B7785"


class Canvas:
    def __init__(self, height_cm, width_cm=14.65, units_w=100.0):
        self.fig = plt.figure(figsize=(width_cm / 2.54, height_cm / 2.54))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.W = units_w
        self.H = units_w * height_cm / width_cm
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)
        self.ax.axis("off")
        self.boxes = {}

    # ---- shapes -----------------------------------------------------------
    def box(self, name, x, y, w, h, text="", fill="blue", fs=7.5, bold=False,
            rounded=True, lw=1.0, ls="-", ha="center", ec=EDGE, tcolor=BLACK, z=2):
        if rounded:
            style = "round,pad=0,rounding_size=%.2f" % (min(w, h) * 0.16)
        else:
            style = "square,pad=0"
        patch = FancyBboxPatch((x, y), w, h, boxstyle=style, fc=FILL.get(fill, fill),
                               ec=ec, lw=lw, ls=ls, zorder=z)
        self.ax.add_patch(patch)
        if text:
            tx = x + w / 2 if ha == "center" else x + 1.6
            self.ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs,
                         fontweight="bold" if bold else "normal", color=tcolor,
                         zorder=z + 1, linespacing=1.25)
        self.boxes[name] = (x, y, w, h)
        return name

    def region(self, x, y, w, h, title, fs=8.5, fill="#F6F8FA", ec="#8A99A8"):
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5",
                               fc=fill, ec=ec, lw=1.0, ls=(0, (4, 3)), zorder=0.5)
        self.ax.add_patch(patch)
        self.ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="center",
                     fontsize=fs, fontweight="bold", color=BLACK, zorder=1)

    def diamond(self, name, cx, cy, w, h, text, fill="amber", fs=7.5):
        pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
        self.ax.add_patch(Polygon(pts, closed=True, fc=FILL.get(fill, fill), ec=EDGE,
                                  lw=1.0, zorder=2))
        self.ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=BLACK,
                     zorder=3, linespacing=1.2)
        self.boxes[name] = (cx - w / 2, cy - h / 2, w, h)

    def ellipse(self, name, cx, cy, w, h, text, fill="green", fs=7.5, bold=False):
        self.ax.add_patch(Ellipse((cx, cy), w, h, fc=FILL.get(fill, fill), ec=EDGE,
                                  lw=1.0, zorder=2))
        self.ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=BLACK,
                     zorder=3, linespacing=1.2, fontweight="bold" if bold else "normal")
        self.boxes[name] = (cx - w / 2, cy - h / 2, w, h)

    # ---- connections ------------------------------------------------------
    def anchor(self, name, side, frac=0.5):
        x, y, w, h = self.boxes[name]
        if side == "l":
            return (x, y + h * frac)
        if side == "r":
            return (x + w, y + h * frac)
        if side == "t":
            return (x + w * frac, y + h)
        return (x + w * frac, y)

    def arrow(self, p1, p2, color=EDGE, lw=1.1, ls="-", head=True, rad=0.0, z=1.5):
        style = "-|>" if head else "-"
        patch = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=8, lw=lw,
                                color=color, ls=ls, shrinkA=0, shrinkB=0,
                                connectionstyle="arc3,rad=%.2f" % rad, zorder=z)
        self.ax.add_patch(patch)

    def path(self, pts, color=EDGE, lw=1.1, ls="-", head=True, z=1.5):
        """Polyline through pts with an arrow head on the last segment."""
        for a, b in zip(pts[:-2], pts[1:-1]):
            self.ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, ls=ls,
                         zorder=z, solid_capstyle="butt")
        self.arrow(pts[-2], pts[-1], color=color, lw=lw, ls=ls, head=head, z=z)

    def label(self, x, y, text, fs=7, bold=False, ha="center", va="center",
              color=BLACK, bg=False, rotation=0, italic=False):
        kw = {}
        if bg:
            kw["bbox"] = dict(fc="white", ec="none", pad=0.8, alpha=0.95)
        self.ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
                     fontweight="bold" if bold else "normal",
                     fontstyle="italic" if italic else "normal",
                     rotation=rotation, zorder=5, linespacing=1.2, **kw)

    def line(self, p1, p2, color=GREY, lw=0.9, ls="--", z=1):
        self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=lw, ls=ls, zorder=z)

    def save(self, path, dpi=300):
        self.fig.savefig(path, dpi=dpi, facecolor="white")
        plt.close(self.fig)
