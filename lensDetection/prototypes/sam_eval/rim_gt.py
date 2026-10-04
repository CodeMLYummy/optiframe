"""Prototype: find the lens outline from its thin rim line, not from background residuals."""
import sys, cv2, numpy as np
from pathlib import Path

SCALE = float(__import__("os").environ.get("SCALE", 0.5))
WEAK = int(__import__('os').environ.get('WEAK', 15))
GAP = int(__import__('os').environ.get('GAP', 151))  # work at half resolution (2040 px wide)
out = Path(sys.argv[1]); photos = sys.argv[2:]

for f in photos:
    name = Path(f).stem[-6:]  # HHMMSS of <lens>_<sheet>_<YYYYMMDD-HHMMSS>.jpg
    img = cv2.imread(f); small = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Thin-line response: top-hat (bright line on dark) + black-hat (dark line on light).
    # Step edges between squares are wider than the kernel on both sides, so they cancel.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    line = cv2.add(cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k),
                   cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k))
    cv2.imwrite(str(out / f"{name}_line.jpg"), cv2.convertScaleAbs(line, alpha=3))
    print(name, "line pct 50/90/99/99.9:", np.percentile(line, [50, 90, 99, 99.9]))

    # --- Keep long, thin pieces: the rim is a long curve, checker corners are dots.
    # Hysteresis: weak line pixels survive only if connected to strong ones.
    weak = (line >= WEAK).astype(np.uint8)
    nw, wl = cv2.connectedComponents(weak, connectivity=8)
    strong_ids = np.unique(wl[line >= 35])
    bw = (np.isin(wl, strong_ids[strong_ids > 0])).astype(np.uint8) * 255
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    min_len = 0.04 * gray.shape[1]
    keep = np.zeros_like(bw)
    pieces = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        diag = np.hypot(w, h)
        # Long and sparse (curve-like), not a filled blob such as a glare spot.
        if diag >= min_len and area / (w * h) < 0.5:
            keep[labels == i] = 255
            pieces.append((diag, i))
    print(f"  {len(pieces)} long thin pieces; longest diags: {sorted(int(d) for d, _ in pieces)[-6:]}")
    if not pieces:
        continue
    # The rim is the subset of pieces that together trace ONE closed ellipse-like curve.
    # Try combinations of the longest pieces; score = angular coverage around the fitted
    # centre, provided the points stay close to the fitted ellipse.
    from itertools import combinations
    H, W = gray.shape
    rng = np.random.default_rng(0)
    top = sorted(pieces, reverse=True)[:10]
    pts_of = {}
    for _, i in top:
        p_ = np.column_stack(np.nonzero(labels == i))[:, ::-1].astype(np.float32)
        pts_of[i] = p_[rng.choice(len(p_), min(300, len(p_)), replace=False)]
    best = None
    for k in range(1, len(top) + 1):
        for subset in combinations([i for _, i in top], k):
            P = np.vstack([pts_of[i] for i in subset])
            if len(P) < 20:
                continue
            (cx, cy), (ea, eb), ang = cv2.fitEllipse(P)
            a, b = ea / 2, eb / 2
            if not (0.05 * W < min(a, b) and max(a, b) < 0.6 * W and max(a, b) / min(a, b) < 3):
                continue
            t = np.deg2rad(ang)
            d = P - (cx, cy)
            u = d[:, 0] * np.cos(t) + d[:, 1] * np.sin(t)
            v = -d[:, 0] * np.sin(t) + d[:, 1] * np.cos(t)
            r = np.sqrt((u / a) ** 2 + (v / b) ** 2)
            rms = float(np.sqrt(np.mean((r - 1) ** 2)))
            if rms > 0.06:
                continue
            bins = np.unique((np.degrees(np.arctan2(v / b, u / a)) // 10).astype(int))
            coverage = len(bins) / 36
            score = (coverage, -rms)
            if best is None or score > best[0]:
                best = (score, subset, rms)
    ov = small.copy()
    ov[keep > 0] = (0, 0, 255)
    if best is None:
        print("  no consistent closed curve found")
        cv2.imwrite(str(out / f"{name}_overlay.jpg"), cv2.resize(ov, None, fx=0.6, fy=0.6))
        continue
    (coverage, _), subset, rms = best
    rim = np.isin(labels, subset).astype(np.uint8) * 255
    pts = cv2.findNonZero(rim)
    hull = cv2.convexHull(pts)
    x, y, w, h = cv2.boundingRect(hull)
    print(f"  lens: {len(subset)} pieces, angular coverage {coverage:.0%}, ellipse rms {rms:.3f}, "
          f"hull {cv2.contourArea(hull) / SCALE**2:.0f} px² (full res), bbox {[int(v / SCALE) for v in (x, y, w, h)]}")
    ov[rim > 0] = (0, 255, 255)
    cv2.drawContours(ov, [hull], -1, (0, 255, 0), 3)
    gm = np.zeros(gray.shape, np.uint8); cv2.drawContours(gm, [hull], -1, 255, -1)
    cv2.imwrite(str(out / f"gt_{name}.png"), gm)  # filled hull mask at SCALE
    cv2.imwrite(str(out / f"{name}_overlay.jpg"), cv2.resize(ov, None, fx=0.6, fy=0.6))
