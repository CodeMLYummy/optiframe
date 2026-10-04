"""v10: smooth rim refinement. v5 finds the loop; a second, fine path search inside a +-0.6 mm band replaces the
per-angle snap, so the outline follows one edge smoothly instead of jumping between nearby lines.

  first pass   v5 dynamic programming (0.4 mm step limit, jump cost) -> which loop is the lens
  refinement   dynamic programming inside +-SNAP_MM around that loop, radius change <= 1 px per 0.5 degree,
               no jump cost (it flattened the long axis), optional outer bias (bonus per px outward) so that of
               two close lines (bevel + side wall) the outer one, the lens edge, wins

usage (from lensDetection/): .venv/bin/python prototypes/v10_smooth_rim/smooth_rim.py
Compares v5 and v10 variants end to end on the 54 caliper photos (v8 detector), see report().
"""

import statistics as st
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
LD = HERE.parents[1]
sys.path.insert(0, str(LD / "prototypes/v5_polar_contour"))
sys.path.insert(0, str(LD / "prototypes/v3_segmenter_tuning"))
sys.path.insert(0, str(LD / "prototypes/v7_v8_v9_detector"))
import measure as pipeline  # noqa: E402
import seg_clear  # noqa: E402

V5 = seg_clear.v5  # the original, kept before measure() gets other segmenters swapped in

PPM = 10
N_ANGLES = 720
R_MAX = int(45 * PPM)
CAP = 6.0
OFF_BAND = 50.0  # penalty per angle spent outside the +-snap band


def refine(raw, first_radii, snap_mm=0.6, outer_bias=0.0, max_step=1):
    """Closed path inside +-snap_mm of `first_radii`, |dr| <= max_step px per angle, maximising capped response
    plus `outer_bias` per px of outward offset (normalised to the band half-width)."""
    k = int(round(snap_mm * PPM))
    R = raw.shape[1]
    radius = np.arange(R)
    # Outside the band is heavily penalised rather than forbidden: the first path is not forced to close
    # exactly (its 0 and 359.5 degree radii can differ), and a hard band would leave no valid path at the seam.
    score = np.full((N_ANGLES, R), -OFF_BAND, np.float32)
    for t in range(N_ANGLES):
        lo, hi = max(0, first_radii[t] - k), min(R - 1, first_radii[t] + k)
        score[t, lo : hi + 1] = (
            np.minimum(raw[t, lo : hi + 1], CAP) + outer_bias * (radius[lo : hi + 1] - first_radii[t]) / k
        )
    rows = np.vstack([score, score])
    n = rows.shape[0]
    acc = rows[0].copy()
    back = np.zeros((n, R), np.int32)
    for t in range(1, n):
        best = np.full(R, -np.inf, np.float32)
        arg = np.zeros(R, np.int32)
        for d in range(-max_step, max_step + 1):
            shifted = np.full(R, -np.inf, np.float32)
            if d >= 0:
                shifted[d:] = acc[: R - d] if d else acc
            else:
                shifted[:d] = acc[-d:]
            better = shifted > best
            best[better] = shifted[better]
            arg[better] = (radius - d)[better]
        acc = best + rows[t]
        back[t] = arg
    r = np.zeros(n, np.int32)
    r[-1] = int(np.argmax(acc))
    for t in range(n - 1, 0, -1):
        r[t - 1] = back[t, r[t]]
    return r[N_ANGLES:]


def v10(win, ppm=PPM, outer_bias=0.0, snap_mm=0.6):
    resp = seg_clear.line_response(win, ppm)
    h, w = resp.shape
    ys, xs = np.nonzero(resp > np.percentile(resp, 99.5))
    center = (float(np.median(xs)), float(np.median(ys))) if len(xs) else (w / 2, h / 2)
    for _ in range(2):
        pts, strength = seg_clear.polar_contour(resp, center, ppm, snap_mm=0)  # first pass only
        used_center = center
        m = cv2.moments(pts.reshape(-1, 1, 2))
        if m["m00"] == 0:
            break
        center = (m["m10"] / m["m00"], m["m01"] / m["m00"])
    mask = np.zeros((h, w), np.uint8)
    if strength < seg_clear.MIN_RIM_COVERAGE:
        return mask
    first = np.round(np.hypot(pts[:, 0] - used_center[0], pts[:, 1] - used_center[1]) - 0.5).astype(int)
    raw = cv2.warpPolar(resp, (R_MAX, N_ANGLES), used_center, R_MAX, cv2.WARP_POLAR_LINEAR)
    radii = refine(raw, first, snap_mm, outer_bias)
    theta = np.arange(N_ANGLES) * 2 * np.pi / N_ANGLES
    out = np.stack([used_center[0] + (radii + 0.5) * np.cos(theta), used_center[1] + (radii + 0.5) * np.sin(theta)], 1)
    cv2.fillPoly(mask, [np.round(out).astype(np.int32)], 255)
    return mask


def roughness(mask):
    """Jaggedness: mean |second difference| of the outline radius around its centroid, in px (0 = smooth)."""
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(float)
    m = cv2.moments(c.astype(np.float32).reshape(-1, 1, 2))
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    ang = np.arctan2(c[:, 1] - cy, c[:, 0] - cx)
    rad = np.hypot(c[:, 0] - cx, c[:, 1] - cy)
    bins = np.floor((ang + np.pi) / (2 * np.pi) * N_ANGLES).astype(int) % N_ANGLES
    r = np.zeros(N_ANGLES)
    np.maximum.at(r, bins, rad)
    r[r == 0] = np.interp(np.flatnonzero(r == 0), np.flatnonzero(r > 0), r[r > 0], period=N_ANGLES)
    return float(np.mean(np.abs(np.roll(r, -1) - 2 * r + np.roll(r, 1))))


def perimeter_ratio(mask):
    """Outline length / convex hull length: 1.00 for a smooth convex lens, larger when jagged."""
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    return cv2.arcLength(c, True) / cv2.arcLength(cv2.convexHull(c), True)


VARIANTS = {
    "v5 (snap)": lambda w, ppm=PPM: V5(w, ppm),
    "v10 bias 0": lambda w, ppm=PPM: v10(w, ppm, 0.0),
    "v10 bias 1": lambda w, ppm=PPM: v10(w, ppm, 1.0),
    "v10 bias 2": lambda w, ppm=PPM: v10(w, ppm, 2.0),
}


def main():
    import csv

    idx = {r["file"]: r for r in csv.DictReader(open(LD / "photos3/index.csv"))}
    photos = [(f, idx[f.name]["lens"]) for f in sorted((LD / "photos3").glob("*_charuco-blank_*.jpg"))]
    photos += [(f, "red") for f in sorted((LD / "photos2").glob("red_charuco-blank_*.jpg"))]
    det = pipeline.detector(*pipeline.VARIANTS["v8"])
    results = {v: [] for v in VARIANTS}
    out = LD / "results_v10"
    out.mkdir(exist_ok=True)
    for f, lens in photos:
        img = cv2.imread(str(f))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        panels = []
        for name, seg in VARIANTS.items():
            pipeline.seg_clear.v5 = seg  # measure() calls seg_clear.v5: swap the segmenter
            images = {}
            status, a, b, _, _ = pipeline.measure(gray, img, det, images)
            rough = perim = None
            if status == "OK":
                rough, perim = roughness(images["mask"]), perimeter_ratio(images["mask"])
            results[name].append(dict(photo=f.name, lens=lens, status=status, A=a, B=b, rough=rough, perim=perim))
            if "window" in images:
                win = images["window"].copy()
                cs, _ = cv2.findContours(images["mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(win, cs, -1, (0, 0, 255), 2)
                cv2.putText(win, name, (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)
                panels.append(win)
        pipeline.seg_clear.v5 = V5
        if panels:
            # crop all panels to the lens area of the first one, for a close look at the edge
            ys, xs = np.nonzero(cv2.inRange(panels[0], (0, 0, 250), (5, 5, 255)))
            if len(xs):
                y0, y1 = max(0, ys.min() - 60), ys.max() + 60
                x0, x1 = max(0, xs.min() - 60), xs.max() + 60
                panels = [p[y0:y1, x0:x1] for p in panels]
            cv2.imwrite(str(out / f.name), np.hstack(panels), [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f.name, flush=True)
    report(results)


def report(results):
    K = pipeline.PRINT_SCALE
    print(
        f"\n{'variant':12} {'measured':>9} {'MAE true':>9} {'signed':>7} {'<=1mm':>7} "
        f"{'roughness px':>12} {'perim/hull':>10} | 005114 error"
    )
    for name, rows in results.items():
        ok = [r for r in rows if r["status"] == "OK"]
        e = []
        for r in ok:
            L, S = pipeline.CALIPER[r["lens"]]
            A, B = max(r["A"], r["B"]) * K, min(r["A"], r["B"]) * K
            e.append((A - L, B - S))
        x = next((r for r in ok if r["photo"].endswith("005114.jpg")), None)
        xe = ""
        if x:
            L, S = pipeline.CALIPER[x["lens"]]
            xe = f"{max(x['A'], x['B']) * K - L:+.2f} x {min(x['A'], x['B']) * K - S:+.2f}"
        print(
            f"{name:12} {len(ok):>4}/{len(rows):<4} {st.mean([abs(v) for p in e for v in p]):9.2f} "
            f"{st.mean([v for p in e for v in p]):+7.2f} {sum(abs(a) <= 1 and abs(b) <= 1 for a, b in e):>3}/{len(e):<3} "
            f"{st.median([r['rough'] for r in ok]):12.2f} {st.median([r['perim'] for r in ok]):10.3f} | {xe}"
        )


if __name__ == "__main__":
    main()
