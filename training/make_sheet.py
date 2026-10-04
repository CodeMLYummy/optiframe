"""Generates the printable reference sheet from backend/src/main/resources/sheet-layout.json.

Usage: python make_sheet.py  ->  frontend/public/feuille-optiframe.pdf
Print at 100 % (no "fit to page") and check the 100 mm ruler with a caliper.
"""

import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "backend/src/main/resources/sheet-layout.json"
OUT = ROOT / "frontend/public/feuille-optiframe.pdf"
MM_PER_INCH = 25.4


def main() -> None:
    layout = json.loads(LAYOUT.read_text())
    w, h = layout["paper"]["widthMm"], layout["paper"]["heightMm"]
    size = layout["markerSizeMm"]
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, layout["dictionary"]))

    fig = plt.figure(figsize=(w / MM_PER_INCH, h / MM_PER_INCH))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)  # y down, like the layout
    ax.axis("off")

    for m in layout["markers"]:
        img = cv2.aruco.generateImageMarker(dictionary, m["id"], 600)
        x, y = m["xMm"], m["yMm"]
        ax.imshow(img, cmap="gray", vmin=0, vmax=255, interpolation="nearest", extent=(x, x + size, y + size, y))

    win = layout["lensWindow"]
    ax.add_patch(
        Rectangle(
            (win["xMm"], win["yMm"]),
            win["widthMm"],
            win["heightMm"],
            fill=False,
            linestyle="--",
            linewidth=0.6,
            edgecolor="0.5",
        )
    )
    cx = win["xMm"] + win["widthMm"] / 2
    cy = win["yMm"] + win["heightMm"] / 2
    # No line across the window: under the lens it would merge with its outline. Short ticks just
    # inside the window edges show the horizontal axis, clear of the lens and of the markers' quiet zone.
    for x0 in (win["xMm"], win["xMm"] + win["widthMm"] - 5):
        ax.plot([x0, x0 + 5], [cy, cy], color="black", linewidth=0.6)
    ax.text(
        cx,
        6,
        "Verre au centre du cadre, face bombée vers le haut, horizontal entre les repères",
        ha="center",
        va="center",
        fontsize=7,
        color="0.3",
    )

    r = layout["checkRuler"]
    ax.plot([r["x1Mm"], r["x2Mm"]], [r["yMm"], r["yMm"]], color="black", linewidth=0.5)
    for x in range(int(r["x1Mm"]), int(r["x2Mm"]) + 1, 10):
        ax.plot([x, x], [r["yMm"] - 2, r["yMm"]], color="black", linewidth=0.5)
    ax.text(
        (r["x1Mm"] + r["x2Mm"]) / 2,
        r["yMm"] + 5,
        "Imprimer à 100 %. Cette règle doit mesurer 100 mm.",
        ha="center",
        fontsize=7,
    )
    ax.text(w / 2, h - 4, layout["name"], ha="center", fontsize=6, color="0.5")

    fig.savefig(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
