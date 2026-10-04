"""Evaluate SAM 2.1 (tiny/small) and SAM ViT-B on the lens photos.

usage: .venv/bin/python run_sam.py [model ...]   (models: sam2t sam2s vitb)
"""
import csv, os, sys, time
import cv2
import numpy as np
import torch
from common import (NAMES, BBOX, FULL, EVAL_SCALE, load, gt_mask, gt_ellipse, iou, boundary_err, _contour, HERE)

torch.set_num_threads(12)
import resource
resource.setrlimit(resource.RLIMIT_AS, (int(os.environ.get("ASLIM_GB", "14")) << 30,) * 2)  # fail fast instead of OOM-killing the desktop
OUT = HERE / "overlays"; OUT.mkdir(exist_ok=True)
EH, EW = int(FULL[0] * EVAL_SCALE), int(FULL[1] * EVAL_SCALE)


def build(name):
    if name.startswith("sam2"):
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
        cfg, ck = {"sam2t": ("t", "tiny"), "sam2s": ("s", "small")}[name]
        m = build_sam2(f"configs/sam2.1/sam2.1_hiera_{cfg}.yaml", str(HERE / f"ckpt/sam2.1_hiera_{ck}.pt"), device="cpu")
        return SAM2ImagePredictor(m), SAM2AutomaticMaskGenerator(m, points_per_side=32, points_per_batch=16, pred_iou_thresh=0.5, stability_score_thresh=0.8)
    from segment_anything import sam_model_registry, SamPredictor, SamAutomaticMaskGenerator
    m = sam_model_registry["vit_b"](checkpoint=str(HERE / "ckpt/sam_vit_b_01ec64.pth"))
    return SamPredictor(m), SamAutomaticMaskGenerator(m, points_per_side=32, points_per_batch=16, pred_iou_thresh=0.5, stability_score_thresh=0.8)


def variant(img, n, kind):
    """Return (image fed to SAM, offset (ox,oy) in full res, scale full->variant)."""
    H, W = img.shape[:2]
    if kind == "full1024":
        s = 1024 / W; return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), (0, 0), s
    if kind == "full512":
        s = 512 / W; return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), (0, 0), s
    if kind == "crop":  # bbox + 40% margin, long side 1024
        x, y, w, h = BBOX[n]
        x0, y0 = max(0, int(x - 0.4 * w)), max(0, int(y - 0.4 * h))
        x1, y1 = min(W, int(x + 1.4 * w)), min(H, int(y + 1.4 * h))
        c = img[y0:y1, x0:x1]; s = 1024 / max(c.shape[:2])
        return cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), (x0, y0), s
    raise ValueError(kind)


def to_eval(mask, off, s):
    """Map a mask in variant coords to a full-frame mask at EVAL_SCALE."""
    out = np.zeros((EH, EW), np.uint8)
    f = EVAL_SCALE / s
    w, h = int(round(mask.shape[1] * f)), int(round(mask.shape[0] * f))
    r = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_LINEAR)
    ox, oy = int(round(off[0] * EVAL_SCALE)), int(round(off[1] * EVAL_SCALE))
    h2, w2 = min(h, EH - oy), min(w, EW - ox)
    out[oy:oy + h2, ox:ox + w2] = r[:h2, :w2]
    return out > 0


def prompts(n):
    x, y, w, h = BBOX[n]
    c = (x + w / 2, y + h / 2)
    neg = [(x - 0.12 * w, c[1]), (x + 1.12 * w, c[1]), (c[0], y - 0.12 * h), (c[0], y + 1.12 * h)]
    return {
        "a_point": dict(pts=[c], lab=[1], box=None),
        "b_box": dict(pts=None, lab=None, box=[x, y, x + w, y + h]),
        "c_point+neg": dict(pts=[c] + neg, lab=[1, 0, 0, 0, 0], box=None),
        "e_box+point": dict(pts=[c], lab=[1], box=[x, y, x + w, y + h]),
        # positive clicks ON the rim (4 extreme points of the GT outline, 8 px inward) + centre negative
        "f_rimclicks": dict(pts=rim_pts(n) + [c], lab=[1, 1, 1, 1, 0], box=None),
        # box sensitivity: the GT-derived box is optimistic, so loosen / shift it
        "g_box_loose10": dict(pts=None, lab=None, box=[x - .1 * w, y - .1 * h, x + 1.1 * w, y + 1.1 * h]),
        "h_box_loose25": dict(pts=None, lab=None, box=[x - .25 * w, y - .25 * h, x + 1.25 * w, y + 1.25 * h]),
        "i_box_shift10": dict(pts=None, lab=None, box=[x + .1 * w, y + .1 * h, x + 1.1 * w, y + 1.1 * h]),
        "j_box_tight10": dict(pts=None, lab=None, box=[x + .1 * w, y + .1 * h, x + .9 * w, y + .9 * h]),
    }


def rim_pts(n):
    cg = _contour(gt_mask(n)) / EVAL_SCALE
    cx, cy = cg.mean(0)
    out = []
    for i in (cg[:, 0].argmin(), cg[:, 0].argmax(), cg[:, 1].argmin(), cg[:, 1].argmax()):
        p = cg[i]; d = np.array([cx, cy]) - p; d /= np.linalg.norm(d)
        out.append(tuple(p + 8 * d))
    return out


def metrics(m, gt, ge, gray):
    f = fill(m)
    be = boundary_err(f, gt)
    ring = 1 - m.sum() / max(f.sum(), 1)  # ~0 for a solid disc, ~0.9 for a thin rim ring
    return dict(iou=round(iou(m, gt), 3), iou_fill=round(iou(f, gt), 3), iou_fill_ellipse=round(iou(f, ge), 3),
                ring=round(float(ring), 2), bnd_mean_px=round(be[0], 1), bnd_p95_px=round(be[1], 1),
                snap=round(snap_frac(f, gt, gray), 3))


def fill(m):
    """Convex hull of the mask's significant components (>=5% of mask area): turns a (possibly
    broken) rim ring into a filled lens disc; leaves a solid convex blob unchanged."""
    out = np.zeros(m.shape, np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n <= 1:
        return out > 0
    tot = st[1:, cv2.CC_STAT_AREA].sum()
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 0.05 * tot]
    pts = cv2.findNonZero(np.isin(lab, keep).astype(np.uint8))
    cv2.drawContours(out, [cv2.convexHull(pts)], -1, 1, -1)
    return out > 0


def snap_frac(pred, gt, gray_eval):
    """Fraction of predicted contour lying on checkerboard edges far (>15 px full-res) from the rim."""
    cp = _contour(pred)
    if len(cp) == 0:
        return float("nan")
    edges = cv2.dilate(cv2.Canny(gray_eval, 60, 150), np.ones((5, 5), np.uint8)) > 0
    e = np.ones(gt.shape, np.uint8); cg = _contour(gt); e[cg[:, 1], cg[:, 0]] = 0
    far = cv2.distanceTransform(e, cv2.DIST_L2, 5) / EVAL_SCALE > 15
    on = edges[cp[:, 1], cp[:, 0]] & far[cp[:, 1], cp[:, 0]]
    return float(on.mean())


def overlay(base, pred, gt, path, pr=None):
    ov = base.copy()
    ov[pred] = (0.55 * ov[pred] + 0.45 * np.array([0, 0, 255])).astype(np.uint8)
    cs, _ = cv2.findContours(gt.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(ov, cs, -1, (0, 255, 0), 2)
    cs, _ = cv2.findContours(pred.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(ov, cs, -1, (0, 0, 255), 2)
    if pr:
        if pr["box"] is not None:
            b = [int(v * EVAL_SCALE) for v in pr["box"]]
            cv2.rectangle(ov, b[:2], b[2:], (255, 128, 0), 2)
        for p, l in zip(pr["pts"] or [], pr["lab"] or []):
            cv2.circle(ov, (int(p[0] * EVAL_SCALE), int(p[1] * EVAL_SCALE)), 9, (0, 255, 255) if l else (255, 0, 255), -1)
    cv2.imwrite(str(path), cv2.resize(ov, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    # zoom on the lens at eval resolution (half of full-res), contours only
    ys, xs = np.nonzero(gt)
    z = base.copy()
    for mm, col in ((gt, (0, 255, 0)), (pred, (0, 0, 255))):
        cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(z, cs, -1, col, 1)
    pad = 40
    z = z[max(0, ys.min() - pad):ys.max() + pad, max(0, xs.min() - pad):xs.max() + pad]
    cv2.imwrite(str(path).replace(".jpg", "_zoom.jpg"), z)


def main(models):
    rows = []
    for mname in models:
        t0 = time.perf_counter(); pred, amg = build(mname); tload = time.perf_counter() - t0
        print(f"### {mname} loaded in {tload:.1f}s", flush=True)
        for n in NAMES:
            img = load(n); gt = gt_mask(n); ge = gt_ellipse(n)
            base = cv2.resize(img, (EW, EH), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
            for vk in ["full1024", "crop", "full512"]:
                vim, off, s = variant(img, n, vk)
                rgb = cv2.cvtColor(vim, cv2.COLOR_BGR2RGB)
                t0 = time.perf_counter()
                with torch.inference_mode():
                    pred.set_image(rgb)
                tenc = time.perf_counter() - t0
                for pk, pr in prompts(n).items():
                    kw = dict(multimask_output=(pk == "a_point"))
                    if pr["pts"] is not None:
                        kw["point_coords"] = np.array([((px - off[0]) * s, (py - off[1]) * s) for px, py in pr["pts"]], np.float32)
                        kw["point_labels"] = np.array(pr["lab"])
                    if pr["box"] is not None:
                        bx = pr["box"]
                        kw["box"] = np.array([(bx[0] - off[0]) * s, (bx[1] - off[1]) * s, (bx[2] - off[0]) * s, (bx[3] - off[1]) * s], np.float32)
                    t0 = time.perf_counter()
                    with torch.inference_mode():
                        masks, scores, _ = pred.predict(**kw)
                    tdec = time.perf_counter() - t0
                    ems = [to_eval(m > 0, off, s) for m in masks]
                    k = int(np.argmax(scores))
                    m = ems[k]
                    row = dict(model=mname, photo=n, variant=vk, prompt=pk,
                               **metrics(m, gt, ge, gray),
                               iou_fill_oracle=round(max(iou(fill(e), gt) for e in ems), 3),
                               score=round(float(scores[k]), 3),
                               t_encode=round(tenc, 2), t_prompt=round(tdec, 3))
                    rows.append(row); print(row, flush=True); dump(rows, models)
                    overlay(base, m, gt, OUT / f"{mname}_{n}_{vk}_{pk}.jpg", pr)
                if vk in ("full1024", "crop") and os.environ.get("AMG", "1") == "1":
                    t0 = time.perf_counter()
                    try:
                        with torch.inference_mode():
                            anns = amg.generate(rgb)
                    except (MemoryError, RuntimeError) as e:
                        print("AMG failed:", mname, n, vk, type(e).__name__, str(e)[:200], flush=True)
                        continue
                    tamg = time.perf_counter() - t0
                    # oracle pick: the auto mask whose FILLED outline best matches GT
                    best, bi = None, -1
                    for a in anns:
                        em = to_eval(a["segmentation"], off, s); v = iou(fill(em), gt)
                        if v > bi: bi, best = v, em
                    row = dict(model=mname, photo=n, variant=vk, prompt="d_auto",
                               **metrics(best, gt, ge, gray), iou_fill_oracle=round(bi, 3),
                               score=len(anns), t_encode=round(tamg, 2), t_prompt=0)
                    rows.append(row); print(row, flush=True); dump(rows, models)
                    if best is not None:
                        overlay(base, best, gt, OUT / f"{mname}_{n}_{vk}_d_auto.jpg")
                    # all auto masks, coloured
                    ov = base.copy(); rng = np.random.default_rng(0)
                    for a in sorted(anns, key=lambda a: -a["area"]):
                        em = to_eval(a["segmentation"], off, s)
                        ov[em] = (0.5 * ov[em] + 0.5 * rng.integers(0, 255, 3)).astype(np.uint8)
                    cv2.imwrite(str(OUT / f"{mname}_{n}_{vk}_d_auto_all.jpg"), cv2.resize(ov, None, fx=0.5, fy=0.5))
                    del anns
        del pred, amg
    import resource; print("done; peak RSS MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)


def dump(rows, models):
    out = HERE / f"results_{'_'.join(models)}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:] or ["sam2t", "sam2s", "vitb"])
