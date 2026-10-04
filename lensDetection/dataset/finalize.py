"""Turn label.html's labels.json into the training set: hand labels + auto labels -> results_dataset/train/.

Window labels are outlines in window pixels (10 px/mm). "corners" labels are on the photo shown at half size: the
4 clicked corners of the printed lens window give the homography that rectifies the photo, exactly like the
sheet detector would have.

usage (from lensDetection/): .venv/bin/python dataset/finalize.py [~/Downloads/labels.json]
Writes results_dataset/train/{images,masks}/*.png and prints each hand label's size against the caliper.
"""

import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

LD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import make_dataset as md  # noqa: E402

OUT = md.OUT / "train"


def order_corners(c, window_mm):
    """Same rule as label.html: clockwise around the centroid, the longer pair of sides is the 165 mm side."""
    c = np.asarray(c, float)
    centre = c.mean(axis=0)
    o = c[np.argsort(np.arctan2(c[:, 1] - centre[1], c[:, 0] - centre[0]))]
    d = lambda a, b: float(np.hypot(*(a - b)))
    w, h = window_mm
    if d(o[0], o[1]) + d(o[2], o[3]) <= d(o[1], o[2]) + d(o[3], o[0]):
        dst = [[0, 0], [w, 0], [w, h], [0, h]]
    else:
        dst = [[0, 0], [0, h], [w, h], [w, 0]]
    return o.astype(np.float32), np.float32(dst)


def photo_path(name):
    folder = "photos2" if name.startswith("red_") else "photos3"
    return LD / folder / f"{name}.jpg"


def main():
    src = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Downloads/labels.json"
    labels = json.loads(src.read_text())
    meta = json.loads((md.OUT / "label/queue.js").read_text().split("=", 1)[1].rstrip(";\n"))
    lens_of = {it["name"]: it for it in meta["items"]}
    window_mm = meta["windowMm"]
    W = md.pipeline.W
    size = (int(round(W["widthMm"] * md.PPM)), int(round(W["heightMm"] * md.PPM)))
    for d in ("images", "masks"):
        shutil.rmtree(OUT / d, ignore_errors=True)
        (OUT / d).mkdir(parents=True)
    hand = 0
    for name, lab in sorted(labels.items()):
        if lab.get("skipped") or len(lab.get("outline", [])) < 3:
            continue
        outline = np.float32(lab["outline"])
        if lab["kind"] == "corners":
            if len(lab["corners"]) != 4:
                print(f"{name}: corners missing, skipped")
                continue
            scale = lab.get("photoScale", 1)
            o, dst = order_corners(np.float32(lab["corners"]) / scale, window_mm)
            H = cv2.getPerspectiveTransform(o, dst * md.PPM)
            window = cv2.warpPerspective(cv2.imread(str(photo_path(name))), H, size)
            outline = cv2.perspectiveTransform((outline / scale)[None], H)[0]
        else:
            window = cv2.imread(str(md.OUT / "windows" / f"{name}.png"))
        mask = np.zeros(window.shape[:2], np.uint8)
        cv2.fillPoly(mask, [np.round(outline).astype(np.int32)], 255)
        cv2.imwrite(str(OUT / "images" / f"{name}.png"), window)
        cv2.imwrite(str(OUT / "masks" / f"{name}.png"), mask)
        hand += 1
        L, S = lens_of[name]["caliper"]
        a, b = md.sizes_mm(mask)
        flag = "" if abs(a - L) <= 1 and abs(b - S) <= 1 else "   <- off by more than 1 mm (rotated lens?)"
        print(f"{name}: {a:.2f} x {b:.2f} vs caliper {L} x {S}{flag}")
    auto = 0
    for f in sorted((md.OUT / "auto/images").glob("*.png")):
        if not (OUT / "images" / f.name).exists():  # a hand label wins over the auto one
            shutil.copy(f, OUT / "images" / f.name)
            shutil.copy(md.OUT / "auto/masks" / f.name, OUT / "masks" / f.name)
            auto += 1
    print(f"\ntraining set: {hand} hand labels + {auto} auto labels = {hand + auto} windows in {OUT}")


if __name__ == "__main__":
    main()
