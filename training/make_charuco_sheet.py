"""Generates the ChArUco reference sheets from backend/src/main/resources/sheet-layout-charuco.json.

Usage: python make_charuco_sheet.py  ->  training/sheets/feuille-{charuco,charuco-ronchi,ronchi}-{a4,letter}.pdf
       python make_charuco_sheet.py --layout sheet-layout-charuco-3.json --tag charuco-3
           -> another layout (e.g. a candidate not used by the backend yet), feuille-<tag>[-ronchi]-<paper>.pdf
  feuille-charuco-*         lens window left blank (backlight, like the ArUco sheet)
  feuille-charuco-ronchi-*  same board, Ronchi lines (half black, half white) in the lens window
  feuille-ronchi-*          Ronchi lines over the whole board area, no markers. Power only: the lens
                            magnification is the ratio of line periods inside and outside the lens, so it
                            needs no scale. The outline is measured on a ChArUco sheet in a second photo.
The board is identical on every paper size, centered on the page: positions in the layout are in board
millimetres, so the detector does not need to know which paper was used.
Print at 100 % (no "fit to page") and check that `checkSquares` squares measure the expected length.
Board corners touching the lens window are not usable and must be ignored by the detector.
"""

import argparse
import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "backend/src/main/resources/sheet-layout-charuco.json"
OUT = Path(__file__).resolve().parent / "sheets"
MM_PER_INCH = 25.4
PX_PER_MM = 20


def board(layout: dict) -> cv2.aruco.CharucoBoard:
    c = layout["charuco"]
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, layout["dictionary"]))
    b = cv2.aruco.CharucoBoard((c["squaresX"], c["squaresY"]), c["squareMm"], c["markerMm"], dictionary)
    b.setLegacyPattern(c["legacyPattern"])
    return b


def lines(ax, x: float, y: float, w: float, h: float, period: float) -> None:
    lx = x
    while lx < x + w:
        ax.add_patch(Rectangle((lx, y), min(period / 2, x + w - lx), h, facecolor="black", edgecolor="none"))
        lx += period


def ronchi_only(layout: dict, paper: str, out: Path) -> None:
    w, h = layout["papers"][paper]["widthMm"], layout["papers"][paper]["heightMm"]
    c = layout["charuco"]
    bw, bh = c["squaresX"] * c["squareMm"], c["squaresY"] * c["squareMm"]
    x, y = (w - bw) / 2, (h - bh) / 2
    period = layout["ronchi"]["periodMm"]

    fig = plt.figure(figsize=(w / MM_PER_INCH, h / MM_PER_INCH))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.axis("off")
    lines(ax, x, y, bw, bh, period)

    ax.text(
        w / 2,
        y - 4,
        "Verre au centre, posé à plat puis surélevé (hauteur notée), puis tourné de 90°",
        ha="center",
        va="center",
        fontsize=7,
        color="0.3",
    )
    n = 50
    ax.text(
        w / 2,
        y + bh + 4,
        f"Imprimer à 100 %. {n} traits noirs = {n * period:g} mm.  |  OptiFrame Ronchi {period:g} mm ({paper})",
        ha="center",
        va="center",
        fontsize=7,
    )

    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")


def sheet(layout: dict, paper: str, ronchi: bool, out: Path) -> None:
    w, h = layout["papers"][paper]["widthMm"], layout["papers"][paper]["heightMm"]
    c = layout["charuco"]
    bw, bh = c["squaresX"] * c["squareMm"], c["squaresY"] * c["squareMm"]
    x, y = (w - bw) / 2, (h - bh) / 2
    img = board(layout).generateImage((bw * PX_PER_MM, bh * PX_PER_MM), marginSize=0, borderBits=1)

    fig = plt.figure(figsize=(w / MM_PER_INCH, h / MM_PER_INCH))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)  # y down, like the layout
    ax.axis("off")
    ax.imshow(img, cmap="gray", vmin=0, vmax=255, interpolation="nearest", extent=(x, x + bw, y + bh, y))

    win = layout["lensWindow"]
    wx, wy, ww, wh = x + win["xMm"], y + win["yMm"], win["widthMm"], win["heightMm"]
    ax.add_patch(Rectangle((wx, wy), ww, wh, facecolor="white", edgecolor="none"))
    if ronchi:
        lines(ax, wx, wy, ww, wh, layout["ronchi"]["periodMm"])
    else:
        cy = wy + wh / 2
        # Short ticks just inside the window edges show the horizontal axis without a line under the lens.
        for x0 in (wx, wx + ww - 5):
            ax.plot([x0, x0 + 5], [cy, cy], color="black", linewidth=0.6)
    ax.add_patch(Rectangle((wx, wy), ww, wh, fill=False, linestyle="--", linewidth=0.6, edgecolor="0.5"))

    ax.text(
        w / 2,
        y - 4,
        "Verre au centre du cadre, face bombée vers le haut",
        ha="center",
        va="center",
        fontsize=7,
        color="0.3",
    )
    n = layout["checkSquares"]
    name = layout["name"] + (f" + Ronchi {layout['ronchi']['periodMm']} mm" if ronchi else "") + f" ({paper})"
    ax.text(
        w / 2,
        y + bh + 4,
        f"Imprimer à 100 %. {n} cases doivent mesurer {n * c['squareMm']} mm.  |  {name}",
        ha="center",
        va="center",
        fontsize=7,
    )

    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the ChArUco reference sheets.")
    ap.add_argument("--layout", type=Path, default=LAYOUT, help="layout JSON (default: the backend's)")
    ap.add_argument("--tag", default="charuco", help="file name tag: feuille-<tag>[-ronchi]-<paper>.pdf")
    args = ap.parse_args()
    layout = json.loads(args.layout.read_text())
    OUT.mkdir(exist_ok=True)
    for paper in layout["papers"]:
        sheet(layout, paper, ronchi=False, out=OUT / f"feuille-{args.tag}-{paper}.pdf")
        sheet(layout, paper, ronchi=True, out=OUT / f"feuille-{args.tag}-ronchi-{paper}.pdf")
        if args.layout == LAYOUT:
            # Ronchi-only: no markers and no window, the same for every layout of this board size.
            ronchi_only(layout, paper, out=OUT / f"feuille-ronchi-{paper}.pdf")


if __name__ == "__main__":
    main()
