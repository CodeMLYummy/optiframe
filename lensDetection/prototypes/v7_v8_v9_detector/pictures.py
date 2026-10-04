"""Pictures for v8: base vs v8 corner detection (v6 overlay) and the lens outline v8 measures, vs calipers.

usage (from lensDetection/): .venv/bin/python prototypes/v7_v8_v9_detector/pictures.py [photo.jpg ...]
Default: the photos v8 rescues plus the largest corner gain. Writes results_v7_v9/v8_pictures/ (gitignored).
"""

import csv
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
LD = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LD / "prototypes/v6_corner_overlay"))
import corner_overlay as v6  # noqa: E402
import measure as m  # noqa: E402

DEFAULT = [
    "lens1_charuco-blank_20261004-004542.jpg",
    "lens2_charuco-blank_20261004-005457.jpg",
    "lens1_charuco-blank_20261004-004730.jpg",
    "lens1_charuco-blank_20261004-004737.jpg",
    "lens2_charuco-blank_20261004-005114.jpg",
]


def lens_panel(path, lens, det, height):
    img = cv2.imread(str(path))
    images = {}
    status, a, b, used, err = m.measure(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), img, det, images)
    if "window" not in images:
        panel = np.zeros((height, int(height * 0.73), 3), np.uint8)
        cv2.putText(panel, status, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return panel
    win = images["window"].copy()
    cs, _ = cv2.findContours(images["mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(win, cs, -1, (0, 0, 255), 3)
    if cs:
        x, y, w, h = cv2.boundingRect(max(cs, key=cv2.contourArea))
        cv2.rectangle(win, (x, y), (x + w, y + h), (255, 140, 0), 2)
    s = height / win.shape[0]
    win = cv2.resize(win, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    lines = [f"v8 lens window: {status}"]
    if a:
        L, S = m.CALIPER[lens]
        A, B = max(a, b), min(a, b)
        lines += [
            f"raw  {A:.2f} x {B:.2f} mm",
            f"true scale {A * m.PRINT_SCALE:.2f} x {B * m.PRINT_SCALE:.2f}",
            f"caliper {L} x {S}",
            f"error {A * m.PRINT_SCALE - L:+.2f} x {B * m.PRINT_SCALE - S:+.2f}",
        ]
    for i, t in enumerate(lines):
        cv2.putText(win, t, (12, 34 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(win, t, (12, 34 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return win


def main():
    names = sys.argv[1:] or DEFAULT
    idx = {r["file"]: r for r in csv.DictReader(open(LD / "photos3/index.csv"))}
    title, board, window = v6.printed_sheet()
    base_det, v8_det = m.detector(*m.VARIANTS["base"]), m.detector(*m.VARIANTS["v8"])
    out = LD / "results_v7_v9" / "v8_pictures"
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        folder = "photos2" if name.startswith("red_") else "photos3"
        path = LD / folder / name
        lens = "red" if folder == "photos2" else idx[name]["lens"]
        pages = []
        for label, det in (("BASE", base_det), ("v8 tryRefineMarkers", v8_det)):
            ov, stats, insets = v6.analyse(path, board, window, det)
            pages.append(v6.compose(ov, stats, insets, f"{title} | {label}"))
        h = max(p.shape[0] for p in pages)
        pages = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 8, cv2.BORDER_CONSTANT) for p in pages]
        pages.append(lens_panel(path, lens, v8_det, h))
        cv2.imwrite(str(out / name), np.hstack(pages), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(out / name, flush=True)


if __name__ == "__main__":
    main()
