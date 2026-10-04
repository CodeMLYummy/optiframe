"""v3: Python mirror of backend ClassicalSegmenter.java, to tune thresholds; scored against a colour reference (red lens).

Input: rectified lens windows saved by the backend (OPTIFRAME_DATASET_DIR), copied to
lensDetection/results_seg/win_<photo>.png. usage (from lensDetection/): .venv/bin/python prototypes/v3_segmenter_tuning/seg_lab.py
"""
from pathlib import Path
import cv2, numpy as np, sys
PPM = 10
NAMES = ['212010', '212014', '212017', '212021', '212023']

def disk(r):
    d = 2 * max(1, r) + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))

def largest_filled(binary, ppm, shape):
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs = [c for c in cs if 225 * ppm * ppm <= cv2.contourArea(c) <= 0.8 * shape[0] * shape[1]]
    m = np.zeros(shape[:2], np.uint8)
    if cs: cv2.drawContours(m, [max(cs, key=cv2.contourArea)], -1, 255, -1)
    return m

def current(win, ppm=PPM, canny=(20, 60), C=10, rel=None):
    g = cv2.GaussianBlur(cv2.cvtColor(win, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    e = cv2.Canny(g, *canny)
    block = int(round(ppm * 3)) | 1
    if rel is None:
        dark = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, C)
    else:  # darker than the local mean by a fraction of the paper brightness
        paper = float(np.median(g))
        dark = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, rel * paper)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, disk(1))
    e = cv2.bitwise_or(e, dark)
    e = cv2.morphologyEx(e, cv2.MORPH_CLOSE, disk(int(round(ppm * 0.4))), iterations=2)
    return largest_filled(e, ppm, win.shape)

def reference(win):
    lab = cv2.cvtColor(win, cv2.COLOR_BGR2LAB).astype(float)
    a = lab[..., 1] - np.median(lab[..., 1])
    m = ((a > 12) * 255).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, disk(5))
    return largest_filled(m, PPM, win.shape)

def score(mask, ref):
    if not mask.any(): return dict(A=0, B=0, iou=0, out=99)
    x, y, w, h = cv2.boundingRect(mask); rx, ry, rw, rh = cv2.boundingRect(ref)
    iou = (cv2.bitwise_and(mask, ref) > 0).sum() / (cv2.bitwise_or(mask, ref) > 0).sum()
    # worst outward leak: distance of mask pixels outside ref
    dt = cv2.distanceTransform(255 - ref, cv2.DIST_L2, 5)
    out = dt[mask > 0].max() / PPM
    return dict(dA=(w - rw) / PPM, dB=(h - rh) / PPM, iou=iou, out=out)

if __name__ == '__main__':
    variants = {
        'current C=10 canny20/60': dict(),
        'C=25': dict(C=25),
        'C=35': dict(C=35),
        'canny40/100': dict(canny=(40, 100)),
        'C=25 canny40/100': dict(C=25, canny=(40, 100)),
        'C=35 canny40/100': dict(C=35, canny=(40, 100)),
        'rel0.15 canny40/100': dict(rel=0.15, canny=(40, 100)),
        'rel0.20 canny40/100': dict(rel=0.20, canny=(40, 100)),
    }
    win_dir = Path(__file__).resolve().parents[2] / 'results_seg'
    wins = {n: cv2.imread(str(win_dir / f'win_{n}.png')) for n in NAMES}
    refs = {n: reference(w) for n, w in wins.items()}
    for v, kw in variants.items():
        s = [score(current(wins[n], **kw), refs[n]) for n in NAMES]
        print(f"{v:24} dA " + " ".join(f"{x['dA']:+5.1f}" for x in s) + " | dB " + " ".join(f"{x['dB']:+5.1f}" for x in s)
              + f" | IoU min {min(x['iou'] for x in s):.3f} | worst leak {max(x['out'] for x in s):.1f} mm")
