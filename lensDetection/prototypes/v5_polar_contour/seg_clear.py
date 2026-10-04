"""v4 and v5: classical segmentation of clear lenses on the blank window, vs the current backend logic.

The rim of a clear lens is a thin, faint line; shadows (lens, cables) are wide soft bands. A thin-line filter
(black-hat + top-hat, ~1.6 mm) answers to the rim and not to the bands.

- v4 (`v4`, kept as the failed attempt): close the rim ring, fill it, open away thin leftovers. Fails whenever the
  faint rim has a gap or a cable touches it (3-10 / 34 windows).
- v5 (`v5`, polar contour): unroll the rim map around the lens centre and find, by dynamic programming, the closed
  path r(theta) with the most rim evidence, with a 0.4 mm step limit and a cost per radius jump, then snaps each
  point to the strongest rim response within 0.6 mm (the jump cost alone flattens the long axis). Bridges gaps,
  ignores cables. Refuses when the path has rim evidence on < MIN_RIM of its length. Ported to the backend's
  ClassicalSegmenter.

usage (from lensDetection/):
  .venv/bin/python prototypes/v5_polar_contour/make_windows.py     # photos3 -> results_session3/windows/
  .venv/bin/python prototypes/v5_polar_contour/seg_clear.py        # table + overlays in results_session3/v5/
Also scores the red lens against its colour mask, from results_seg/win_*.png (see v3_segmenter_tuning).
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v3_segmenter_tuning"))
import seg_lab  # noqa: E402  (mirror of the current backend segmenter)

PPM = 10
MIN_RIM_COVERAGE = float(__import__("os").environ.get("MIN_RIM", 0.5))
HERE = Path(__file__).resolve().parents[2]


def disk(r):
    return seg_lab.disk(r)


def v4(win, ppm=PPM, weak_x=2.0, strong_x=4.0, dark_c=25):
    g = cv2.GaussianBlur(cv2.cvtColor(win, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    k = disk(int(round(0.8 * ppm)))
    line = cv2.add(cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(g, cv2.MORPH_TOPHAT, k))
    # Hysteresis, scaled to this photo's background (backlit paper texture can reach 15-20):
    # faint rim pixels are kept when they connect to clearly visible ones.
    noise = max(5.0, float(np.percentile(line, 90)))
    weak, strong = max(10.0, weak_x * noise), max(22.0, strong_x * noise)
    n, lab = cv2.connectedComponents((line >= weak).astype(np.uint8), connectivity=8)
    keep = np.unique(lab[line >= strong])
    rim = np.isin(lab, keep[keep > 0]).astype(np.uint8) * 255
    block = int(round(ppm * 3)) | 1
    dark = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, dark_c)
    m = cv2.bitwise_or(rim, cv2.morphologyEx(dark, cv2.MORPH_OPEN, disk(1)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, disk(int(round(0.5 * ppm))))
    # Fill everything not reachable from the window border: the inside of a closed rim.
    # A 1 px empty frame lets the fill reach every border gap, even where the printed window outline runs.
    ff = cv2.copyMakeBorder(m, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    cv2.floodFill(ff, None, (0, 0), 128)
    filled = np.where(ff[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)
    # Thin things (cables, their shadows' edges, texture) vanish; the filled lens stays.
    filled = cv2.morphologyEx(filled, cv2.MORPH_OPEN, disk(int(round(2 * ppm))))
    return seg_lab.largest_filled(filled, ppm, win.shape)


def line_response(win, ppm=PPM):
    """Thin-line strength (dark or bright, ~1.6 mm), divided by this photo's background level."""
    g = cv2.GaussianBlur(cv2.cvtColor(win, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    k = disk(int(round(0.8 * ppm)))
    line = cv2.add(cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(g, cv2.MORPH_TOPHAT, k))
    noise = max(5.0, float(np.percentile(line, 90)))
    resp = line.astype(np.float32) / noise
    m = int(2 * ppm)  # ignore the printed window outline and its ticks
    resp[:m, :] = resp[-m:, :] = 0
    resp[:, :m] = resp[:, -m:] = 0
    return resp


def polar_contour(resp, center, ppm=PPM, n_angles=720, r_min_mm=8, r_max_mm=45, max_step=4, jump_cost=0.4, snap_mm=0.6):
    """Closed path r(theta) maximising the rim response, |dr| <= max_step px between neighbouring angles."""
    r_max = int(r_max_mm * ppm)
    raw = cv2.warpPolar(resp, (r_max, n_angles), center, r_max, cv2.WARP_POLAR_LINEAR)
    pol = np.minimum(raw, 6.0)  # one very strong blob (glare) must not outweigh a whole faint rim
    pol[:, : int(r_min_mm * ppm)] = 0
    # Unroll 2 turns so the path closes on itself; keep the second turn.
    score = np.vstack([pol, pol])
    n, R = score.shape
    acc = score[0].copy()
    back = np.zeros((n, R), np.int32)
    idx = np.arange(R)
    for t in range(1, n):
        best = np.full(R, -np.inf, np.float32)
        arg = np.zeros(R, np.int32)
        for d in range(-max_step, max_step + 1):
            shifted = np.full(R, -np.inf, np.float32)
            if d >= 0:
                shifted[d:] = acc[: R - d] if d else acc
            else:
                shifted[:d] = acc[-d:]
            shifted = shifted - jump_cost * abs(d)  # detours (to a cable, a glare) cost something
            better = shifted > best
            best[better] = shifted[better]
            arg[better] = (idx - d)[better]
        acc = best + score[t]
        back[t] = arg
    r = np.zeros(n, np.int32)
    r[-1] = int(np.argmax(acc))
    for t in range(n - 1, 0, -1):
        r[t - 1] = back[t, r[t]]
    radii = r[n_angles:]
    strength = float(np.mean(pol[np.arange(n_angles), np.clip(radii, 0, R - 1)] > 2.0))
    # The jump cost flattens the path (cuts the ends of the long axis): snap each point to the strongest
    # response within snap_mm. Same as the backend's ClassicalSegmenter.
    k = int(round(snap_mm * ppm))
    if k:
        snapped = radii.copy()
        for t, rr in enumerate(radii):
            lo, hi = max(0, rr - k), min(R - 1, rr + k)
            band = raw[t, lo : hi + 1]
            snapped[t] = lo + int(np.argmax(band)) if band[np.argmax(band)] > raw[t, rr] else rr
        radii = snapped
    theta = np.arange(n_angles) * 2 * np.pi / n_angles
    pts = np.stack([center[0] + (radii + 0.5) * np.cos(theta), center[1] + (radii + 0.5) * np.sin(theta)], 1)
    return pts.astype(np.float32), strength


def v5(win, ppm=PPM):
    resp = line_response(win, ppm)
    h, w = resp.shape
    # Seed: centre of the strongest thin-line pixels, then re-centre on the found contour once.
    ys, xs = np.nonzero(resp > np.percentile(resp, 99.5))
    center = (float(np.median(xs)), float(np.median(ys))) if len(xs) else (w / 2, h / 2)
    for _ in range(2):
        pts, strength = polar_contour(resp, center, ppm)
        m = cv2.moments(pts.reshape(-1, 1, 2))
        if m["m00"] == 0:
            break
        center = (m["m10"] / m["m00"], m["m01"] / m["m00"])
    mask = np.zeros((h, w), np.uint8)
    # Require the path to sit on rim evidence along most of its length, otherwise report nothing.
    if strength >= MIN_RIM_COVERAGE:
        cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 255)
    return mask


def dims(mask):
    if not mask.any():
        return None
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    H, W = mask.shape
    if x <= 1 or y <= 1 or x + w >= W - 1 or y + h >= H - 1:
        return "edge"
    (_, _), (a, b), _ = cv2.minAreaRect(c)
    return (max(a, b) + 1) / PPM, (min(a, b) + 1) / PPM


def striped(win):
    g = cv2.cvtColor(win, cv2.COLOR_BGR2GRAY).astype(float)
    return g[20:-20, 20:-20].mean(axis=0).std() > 15


if __name__ == "__main__":
    out = HERE / "results_session3" / "v5"
    out.mkdir(exist_ok=True)
    rows = []
    for f in sorted((HERE / "results_session3" / "windows").glob("win_*.png")):
        win = cv2.imread(str(f))
        if striped(win):
            continue
        old = dims(seg_lab.current(win, C=25, canny=(40, 100)))
        new_mask = v5(win)
        new = dims(new_mask)
        rows.append((f.stem[4:], old, new))
        ov = win.copy()
        cs, _ = cv2.findContours(new_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cs, -1, (0, 0, 255), 3)
        cv2.imwrite(str(out / f"{f.stem[4:]}.jpg"), cv2.resize(ov, None, fx=0.25, fy=0.25))

    def fmt(d):
        return "  —  fail   " if d is None else ("  edge      " if d == "edge" else f"{d[0]:5.1f}×{d[1]:4.1f} ")

    print(f"{'photo':10} {'current':12} {'v5':12} lens")
    groups = {"lens 1 (~50×31)": [], "lens 2 (~52×38)": []}
    for p, o, n in rows:
        lens = "" if not isinstance(n, tuple) else ("1" if n[1] < 35 else "2")
        if lens:
            groups["lens 1 (~50×31)" if lens == "1" else "lens 2 (~52×38)"].append(n)
        print(f"{p:10} {fmt(o)} {fmt(n)} {lens}")
    ok_old = sum(isinstance(o, tuple) for _, o, _ in rows)
    ok_new = sum(isinstance(n, tuple) for _, _, n in rows)
    print(f"\nblank windows: {len(rows)} | measured: current {ok_old}, v5 {ok_new}")
    for k, v in groups.items():
        if v:
            a = np.array(v)
            print(
                f"{k}: n={len(v)} long {a[:, 0].mean():.2f} ± {a[:, 0].std():.2f} (range {a[:, 0].min():.1f}–{a[:, 0].max():.1f}), "
                f"short {a[:, 1].mean():.2f} ± {a[:, 1].std():.2f} (range {a[:, 1].min():.1f}–{a[:, 1].max():.1f})"
            )
    # Tinted red lens (session 2): v4 must not regress against the colour reference.
    print("\nred lens (session 2), A × B sheet axes vs colour reference:")
    for n in seg_lab.NAMES:
        w = cv2.imread(str(HERE / "results_seg" / f"win_{n}.png"))
        s = seg_lab.score(v5(w), seg_lab.reference(w))
        if "dA" not in s:
            print(f"  {n}: not found")
            continue
        print(f"  {n}: dA {s['dA']:+.1f} dB {s['dB']:+.1f} IoU {s['iou']:.3f} worst leak {s['out']:.1f} mm")
