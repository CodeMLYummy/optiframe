from pathlib import Path
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
PHOTOS = HERE.parents[1] / "photos1"  # lensDetection/photos1
NAMES = ["005615746", "005617784", "005621479"]
FULL = (3072, 4080)  # H, W
EVAL_SCALE = 0.5     # metrics computed on a 2040x1536 frame, distances reported in full-res px
# Approximate ground-truth bboxes (full res) from the classical rim prototype.
BBOX = {"005615746": [1300, 1128, 1340, 944],
        "005617784": [1440, 1103, 990, 705],
        "005621479": [1134, 830, 1822, 1298]}


def load(n):
    return cv2.imread(str(PHOTOS / f"PXL_20261004_{n}.MP.jpg"))


def gt_mask(n):
    """Proxy GT at EVAL_SCALE: filled convex hull of the rim from rim_proto (SCALE=0.5, WEAK=20).
    For 005617784 (where the prototype is unreliable) the 005615746 hull is warped into its bbox
    (same lens, both shot top-down)."""
    H, W = int(FULL[0] * EVAL_SCALE), int(FULL[1] * EVAL_SCALE)
    if n == "005617784":
        src = cv2.imread(str(HERE / "gt" / "gt_005615746.png"), 0)
        ys, xs = np.nonzero(src)
        crop = src[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        x, y, w, h = [int(round(v * EVAL_SCALE)) for v in BBOX[n]]
        m = np.zeros((H, W), np.uint8)
        m[y:y + h, x:x + w] = cv2.resize(crop, (w, h), interpolation=cv2.INTER_NEAREST)
        return m > 0
    src = cv2.imread(str(HERE / "gt" / f"gt_{n}.png"), 0)
    return cv2.resize(src, (W, H), interpolation=cv2.INTER_NEAREST) > 0


def gt_ellipse(n):
    H, W = int(FULL[0] * EVAL_SCALE), int(FULL[1] * EVAL_SCALE)
    x, y, w, h = [v * EVAL_SCALE for v in BBOX[n]]
    m = np.zeros((H, W), np.uint8)
    cv2.ellipse(m, (int(x + w / 2), int(y + h / 2)), (int(w / 2), int(h / 2)), 0, 0, 360, 1, -1)
    return m > 0


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def _contour(m):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return np.vstack(cs).reshape(-1, 2) if cs else np.zeros((0, 2), int)


def boundary_err(pred, gt):
    """Mean and 95th-pct distance (full-res px) from pred contour to gt contour."""
    cp = _contour(pred)
    if len(cp) == 0:
        return float("nan"), float("nan")
    edge = np.ones(gt.shape, np.uint8)
    cg = _contour(gt)
    edge[cg[:, 1], cg[:, 0]] = 0
    dt = cv2.distanceTransform(edge, cv2.DIST_L2, 5)
    d = dt[cp[:, 1], cp[:, 0]] / EVAL_SCALE
    return float(d.mean()), float(np.percentile(d, 95))
