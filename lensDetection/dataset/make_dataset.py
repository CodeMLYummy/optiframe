"""Build the segmentation dataset: rectified lens windows, auto labels checked against the calipers, and the queue
of windows to label by hand (label.html).

For every photo of photos2/photos3 where the ChArUco sheet is found (v8 detector, the backend's rectification at
10 px/mm), the lens window is saved and the v10 polar contour (the backend's classical segmenter) is run.
  auto      blank window whose v10 outline matches the caliper within AUTO_TOLERANCE_MM on both A and B
  queue     v10 failed or is off; v10's attempt, if any, is kept as a suggestion
  optional  Ronchi windows (the classical method cannot label them), to label if there is time
  corners   sharp photos where the sheet detector fails: the user clicks the 4 corners of the lens window,
            then the outline, on the photo itself (HAND_CORNERS)
  excluded  photos the app should not accept (EXCLUDED, with the reason), not in the dataset

usage (from lensDetection/): .venv/bin/python dataset/make_dataset.py
Writes results_dataset/ (gitignored): windows/*.png, auto/masks/*.png, label/ (images + queue.js for label.html).
"""

import csv
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

LD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LD / "prototypes/v10_smooth_rim"))
sys.path.insert(0, str(LD / "prototypes/v7_v8_v9_detector"))
import measure as pipeline  # noqa: E402
import smooth_rim  # noqa: E402

PPM = 10
AUTO_TOLERANCE_MM = 1.0
CALIPER = {"lens1": (49.5, 30.5), "lens2": (51.4, 38.4), "red": (55.7, 46.5)}
PRINT_SCALE = 73.4 / 75.0  # the sheet these photos were taken on
OUT = LD / "results_dataset"
# Taken outside what the app asks for: not in the dataset.
EXCLUDED = {
    "lens2_charuco-blank_20261004-005403": "no backlight",
    "lens2_charuco-blank_20261004-005405": "no backlight",
    "lens2_charuco-blank_20261004-005406": "no backlight",
    "lens1_charuco-blank_20261004-004543": "steep shot (24 degrees)",
    "lens1_charuco-blank_20261004-004734": "sheet cropped",
    "lens1_charuco-blank_20261004-004736": "sheet cropped",
    "lens1_charuco-blank_20261004-004544": "motion blur",
    "lens2_charuco-blank_20261004-005407": "motion blur",
    "lens2_charuco-blank_20261004-005408": "motion blur",
    "lens2_charuco-blank_20261004-005410": "motion blur",
}
# Sharp photos the sheet detector misses: window corners clicked by hand.
HAND_CORNERS = {
    "lens2_charuco-blank_20261004-005450",
    "red_charuco-blank_20261003-212019",
    "red_charuco-blank_20261003-212025",
}
HAND_SCALE = 0.5  # photos shown at half size in label.html; clicks are scaled back


def rectified_window(img, det):
    """Lens window at 10 px/mm, as the backend crops it, or None when the sheet is not usable."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, _, _ = det.detectBoard(gray)
    if ids is None:
        return None
    obj = pipeline.BOARD_CORNERS[ids.ravel()]
    keep = np.array([not pipeline.on_window_edge(x, y) for x, y in obj])
    if keep.sum() < 8:
        return None
    H, _ = cv2.findHomography(corners.reshape(-1, 2)[keep], obj[keep] * PPM, cv2.RANSAC, 0.3 * PPM)
    if H is None:
        return None
    W = pipeline.W
    rect = cv2.warpPerspective(img, H, (int(180 * PPM), int(255 * PPM)))
    x, y, w, h = (int(round(v * PPM)) for v in (W["xMm"], W["yMm"], W["widthMm"], W["heightMm"]))
    return rect[y : y + h, x : x + w]


def outline(mask, n=96):
    """Up to n points of the mask's outer contour, in window pixels."""
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea).reshape(-1, 2)
    step = max(1, len(c) // n)
    return c[::step].tolist()


def sizes_mm(mask):
    """(long, short) side of the sheet-axis box in real mm (print scale applied)."""
    x, y, w, h = cv2.boundingRect(mask)
    a, b = (w + 1) / PPM * PRINT_SCALE, (h + 1) / PPM * PRINT_SCALE
    return max(a, b), min(a, b)


def main():
    idx = {r["file"]: r for r in csv.DictReader(open(LD / "photos3/index.csv"))}
    photos = [(f, idx[f.name]["lens"], idx[f.name]["sheet"]) for f in sorted((LD / "photos3").glob("*.jpg"))]
    for f in sorted((LD / "photos2").glob("*.jpg")):
        photos.append((f, "red", f.name.split("_")[1]))
    det = pipeline.detector(*pipeline.VARIANTS["v8"])
    for d in ("windows", "auto/images", "auto/masks", "label/img"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    queue, auto, excluded = [], 0, []
    for f, lens, sheet in photos:
        if sheet == "ronchi":  # no markers: no rectification possible
            continue
        if f.stem in EXCLUDED:
            excluded.append(f"{f.stem} ({EXCLUDED[f.stem]})")
            continue
        img = cv2.imread(str(f))
        L, S = CALIPER[lens]
        if f.stem in HAND_CORNERS:
            small = cv2.resize(img, None, fx=HAND_SCALE, fy=HAND_SCALE, interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(OUT / "label/img" / (f.stem + ".jpg")), small, [cv2.IMWRITE_JPEG_QUALITY, 92])
            queue.append(
                dict(
                    name=f.stem,
                    lens=lens,
                    sheet=sheet,
                    caliper=[L, S],
                    width=small.shape[1],
                    height=small.shape[0],
                    kind="corners",
                    photoScale=HAND_SCALE,
                    suggestion=None,
                    v10=None,
                )
            )
            print(f"{f.name}: corners (by hand)", flush=True)
            continue
        win = rectified_window(img, det)
        if win is None:
            print(f"{f.name}: sheet not usable", flush=True)
            continue
        name = f.stem + ".png"
        cv2.imwrite(str(OUT / "windows" / name), win)
        mask = (
            smooth_rim.v10(win, PPM, outer_bias=1.0) if sheet == "charuco-blank" else np.zeros(win.shape[:2], np.uint8)
        )
        status, suggestion, measured = ("queue" if sheet == "charuco-blank" else "optional"), None, None
        if mask.any():
            measured = sizes_mm(mask)
            suggestion = outline(mask)
            if abs(measured[0] - L) <= AUTO_TOLERANCE_MM and abs(measured[1] - S) <= AUTO_TOLERANCE_MM:
                status = "auto"
        if status == "auto":
            auto += 1
            cv2.imwrite(str(OUT / "auto/images" / name), win)
            cv2.imwrite(str(OUT / "auto/masks" / name), mask)
        else:
            cv2.imwrite(str(OUT / "label/img" / (f.stem + ".jpg")), win, [cv2.IMWRITE_JPEG_QUALITY, 92])
            queue.append(
                dict(
                    name=f.stem,
                    lens=lens,
                    sheet=sheet,
                    caliper=[L, S],
                    width=win.shape[1],
                    height=win.shape[0],
                    kind=status,
                    suggestion=suggestion,
                    v10=[round(v, 2) for v in measured] if measured else None,
                )
            )
        print(
            f"{f.name}: {status}" + (f" v10 {measured[0]:.2f} x {measured[1]:.2f} vs {L} x {S}" if measured else ""),
            flush=True,
        )
    window_mm = [pipeline.W["widthMm"], pipeline.W["heightMm"]]
    meta = dict(ppm=PPM, printScale=PRINT_SCALE, windowMm=window_mm, items=queue)
    (OUT / "excluded.txt").write_text("\n".join(excluded) + "\n")
    shutil.copy(Path(__file__).parent / "label.html", OUT / "label/label.html")
    (OUT / "label/queue.js").write_text("window.QUEUE = " + json.dumps(meta) + ";\n")
    count = lambda k: sum(q["kind"] == k for q in queue)
    print(
        f"\nauto-labelled {auto} | to label: {count('queue')} blank + {count('corners')} with corners | "
        f"optional Ronchi windows {count('optional')} | excluded {len(excluded)}"
    )


if __name__ == "__main__":
    main()
