"""v7-v9: ChArUco detector settings, end to end (rectify -> v5 polar contour -> A x B), against caliper values.

  base  CharucoParameters defaults (the backend today)
  v7    minMarkers = 1      a corner needs only one of its two neighbouring markers
  v8    tryRefineMarkers    look again for missed markers using the board layout
  v9    both

The pipeline mirrors the backend: Rectifier (sub-pixel markers, corners on the lens-window edge skipped,
RANSAC homography at 0.3 px/mm-scaled threshold, mean reprojection error over all points <= 0.5 mm, 10 px/mm),
the lens window, ClassicalSegmenter (v5 with the 0.6 mm snap, prototypes/v5_polar_contour) and ContourMeasurer
(contour smoothed over +-0.5 mm, A x B = sheet-axis box). Scores use the caliper values and are given raw and
at the true print scale of the sheet used for photos2/photos3 (5 squares = 73.4 mm, not 75.0).

usage (from lensDetection/): .venv/bin/python prototypes/v7_v8_v9_detector/measure.py
Writes results_v7_v9/measurements.csv (gitignored).
"""

import csv
import json
import statistics as st
import sys
from pathlib import Path

import cv2
import numpy as np

LD = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LD / "prototypes/v5_polar_contour"))
sys.path.insert(0, str(LD / "prototypes/v3_segmenter_tuning"))
import seg_clear  # noqa: E402

PPM = 10.0
MAX_REPROJECTION_MM = 0.5
PRINT_SCALE = 73.4 / 75.0
CALIPER = {"lens1": (49.5, 30.5), "lens2": (51.4, 38.4), "red": (55.7, 46.5)}
VARIANTS = {"base": (2, False), "v7": (1, False), "v8": (2, True), "v9": (1, True)}

layout = json.loads((LD.parent / "backend/src/main/resources/sheet-layout-charuco.json").read_text())
C, W = layout["charuco"], layout["lensWindow"]
board = cv2.aruco.CharucoBoard(
    (C["squaresX"], C["squaresY"]),
    C["squareMm"],
    C["markerMm"],
    cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, layout["dictionary"])),
)
board.setLegacyPattern(C["legacyPattern"])
BOARD_CORNERS = board.getChessboardCorners()[:, :2].astype(np.float32)


def detector(min_markers, refine):
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    cp = cv2.aruco.CharucoParameters()
    cp.minMarkers = min_markers
    cp.tryRefineMarkers = refine
    return cv2.aruco.CharucoDetector(board, cp, params)


def on_window_edge(x, y, margin=0.5):
    return (
        W["xMm"] - margin <= x <= W["xMm"] + W["widthMm"] + margin
        and W["yMm"] - margin <= y <= W["yMm"] + W["heightMm"] + margin
    )


def measure(gray, img, det, images=None):
    """(status, A, B, corners used, mean reprojection mm) like /api/measure; fills `images` (window, mask) if given."""
    corners, ids, _, _ = det.detectBoard(gray)
    if ids is None:
        return "MARKERS_NOT_FOUND", None, None, 0, None
    obj = BOARD_CORNERS[ids.ravel()]
    keep = np.array([not on_window_edge(x, y) for x, y in obj])
    if keep.sum() < 8:
        return "MARKERS_NOT_FOUND", None, None, int(keep.sum()), None
    src = corners.reshape(-1, 2)[keep]
    dst = obj[keep] * PPM
    H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 0.3 * PPM)
    if H is None:
        return "MARKERS_NOT_FOUND", None, None, int(keep.sum()), None
    err_mm = float(np.mean(np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0] - dst, axis=1))) / PPM
    if err_mm > MAX_REPROJECTION_MM:
        return "SCALE_CHECK_FAILED", None, None, int(keep.sum()), err_mm
    rect = cv2.warpPerspective(img, H, (int(180 * PPM), int(255 * PPM)))
    x, y, w, h = (int(round(v * PPM)) for v in (W["xMm"], W["yMm"], W["widthMm"], W["heightMm"]))
    window = rect[y : y + h, x : x + w]
    mask = seg_clear.v5(window, PPM)
    if images is not None:
        images.update(window=window, mask=mask)
    if not mask.any():
        return "LENS_NOT_FOUND", None, None, int(keep.sum()), err_mm
    bx, by, bw, bh = cv2.boundingRect(mask)
    if bx <= 1 or by <= 1 or bx + bw >= w - 1 or by + bh >= h - 1:
        return "LENS_OUT_OF_WINDOW", None, None, int(keep.sum()), err_mm
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(float)
    k = max(1, round(PPM * 0.5))  # ContourMeasurer: circular moving average
    sm = np.stack(
        [np.convolve(np.r_[c[-k:, i], c[:, i], c[:k, i]], np.ones(2 * k + 1) / (2 * k + 1), "valid") for i in (0, 1)], 1
    )
    a = (sm[:, 0].max() - sm[:, 0].min() + 1) / PPM
    b = (sm[:, 1].max() - sm[:, 1].min() + 1) / PPM
    return "OK", a, b, int(keep.sum()), err_mm


def main():
    idx = {r["file"]: r for r in csv.DictReader(open(LD / "photos3/index.csv"))}
    photos = [(f, idx[f.name]["lens"]) for f in sorted((LD / "photos3").glob("*_charuco-blank_*.jpg"))]
    photos += [(f, "red") for f in sorted((LD / "photos2").glob("red_charuco-blank_*.jpg"))]
    dets = {name: detector(*cfg) for name, cfg in VARIANTS.items()}
    rows = []
    for f, lens in photos:
        img = cv2.imread(str(f))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for name, det in dets.items():
            status, a, b, used, err = measure(gray, img, det)
            rows.append(
                dict(
                    photo=f.name,
                    lens=lens,
                    variant=name,
                    status=status,
                    corners_used=used,
                    reprojection_mm=round(err, 3) if err is not None else "",
                    A_mm=round(a, 2) if a else "",
                    B_mm=round(b, 2) if b else "",
                )
            )
        print(f.name, " ".join(f"{r['variant']}:{r['status'][:6]}" for r in rows[-4:]), flush=True)
    out = LD / "results_v7_v9"
    out.mkdir(exist_ok=True)
    with open(out / "measurements.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    report(rows, len(photos))


def errors(rows, scale):
    e = []
    for r in rows:
        L, S = CALIPER[r["lens"]]
        A, B = r["A_mm"] * scale, r["B_mm"] * scale
        e.append((max(A, B) - L, min(A, B) - S))
    return e


def report(rows, n_photos):
    ok_by = {v: {r["photo"] for r in rows if r["variant"] == v and r["status"] == "OK"} for v in VARIANTS}
    common = set.intersection(*ok_by.values())
    print(f"\n{n_photos} blank-window photos with a known lens; {len(common)} measured by every variant")
    head = (
        f"{'variant':6} {'measured':>9} {'fail: sheet/scale/lens/edge':>28} {'corners':>8} | "
        f"{'MAE raw':>7} {'MAE true':>8} {'signed':>7} {'<=1mm':>6} | {'common: MAE true':>16}"
    )
    print(head)
    for v in VARIANTS:
        rv = [r for r in rows if r["variant"] == v]
        ok = [r for r in rv if r["status"] == "OK"]
        fails = [
            sum(r["status"] == s for r in rv)
            for s in ("MARKERS_NOT_FOUND", "SCALE_CHECK_FAILED", "LENS_NOT_FOUND", "LENS_OUT_OF_WINDOW")
        ]
        raw = errors(ok, 1.0)
        true = errors(ok, PRINT_SCALE)
        com = errors([r for r in ok if r["photo"] in common], PRINT_SCALE)
        mae = lambda e: st.mean([abs(x) for p in e for x in p])
        print(
            f"{v:6} {len(ok):>4}/{len(rv):<4} {'/'.join(map(str, fails)):>28} "
            f"{st.median([r['corners_used'] for r in rv]):>8} | {mae(raw):7.2f} {mae(true):8.2f} "
            f"{st.mean([x for p in true for x in p]):+7.2f} {sum(abs(a) <= 1 and abs(b) <= 1 for a, b in true):>3}/{len(true):<3}"
            f"| {mae(com):16.2f}"
        )


if __name__ == "__main__":
    main()
