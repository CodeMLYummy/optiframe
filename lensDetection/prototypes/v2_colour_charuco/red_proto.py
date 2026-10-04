"""v2 prototype: measure a tinted lens on the printed OptiFrame ChArUco sheet (board-plane mm).

usage (from lensDetection/): .venv/bin/python prototypes/v2_colour_charuco/red_proto.py photos2/*.jpg
Writes overlays, contours (mm) and measurements.json to lensDetection/results_red/.
"""
import json, sys, cv2, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L = json.loads((ROOT / "backend/src/main/resources/sheet-layout-charuco.json").read_text())
C, WIN = L["charuco"], L["lensWindow"]
PPM = 10  # rectified pixels per mm
OUT = Path(__file__).resolve().parents[2] / "results_red"
OUT.mkdir(exist_ok=True)

dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, L["dictionary"]))
board = cv2.aruco.CharucoBoard((C["squaresX"], C["squaresY"]), C["squareMm"], C["markerMm"], dictionary)
board.setLegacyPattern(C["legacyPattern"])
detector = cv2.aruco.CharucoDetector(board)
BW, BH = C["squaresX"] * C["squareMm"], C["squaresY"] * C["squareMm"]

rows = []
for f in sys.argv[1:]:
    name = Path(f).stem
    img = cv2.imread(f)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, _, _ = detector.detectBoard(gray)
    if ids is None or len(ids) < 8:
        print(f"{name}: board not found ({0 if ids is None else len(ids)} corners)"); continue
    obj = board.getChessboardCorners()[ids.ravel(), :2].astype(np.float32)
    H, inl = cv2.findHomography(obj, corners.reshape(-1, 2), cv2.RANSAC, 3.0)
    proj = cv2.perspectiveTransform(obj[inl.ravel() > 0][:, None], H).reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum((proj - corners.reshape(-1, 2)[inl.ravel() > 0]) ** 2, 1))))
    # Rectify the whole board into mm space.
    S = np.diag([PPM, PPM, 1.0])
    rect = cv2.warpPerspective(img, S @ np.linalg.inv(H), (BW * PPM, BH * PPM))
    x0, y0, w, h = (int(v * PPM) for v in (WIN["xMm"], WIN["yMm"], WIN["widthMm"], WIN["heightMm"]))
    m = 2 * PPM  # stay 2 mm inside the window (avoid dashed border)
    win = rect[y0 + m:y0 + h - m, x0 + m:x0 + w - m]
    # Tint: Lab a* (red-green) relative to the paper; paper and shadows are neutral.
    lab = cv2.cvtColor(win, cv2.COLOR_BGR2LAB).astype(np.float32)
    a = lab[..., 1] - np.median(lab[..., 1])
    a8 = np.clip(a * 4, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(cv2.GaussianBlur(a8, (5, 5), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Black Ronchi bars inside the lens carry no colour: close across one 2 mm period.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        print(f"{name}: no lens"); continue
    c = max(cs, key=cv2.contourArea)
    (_, _), (rw, rh), ang = cv2.minAreaRect(c)
    bx, by, bw_, bh_ = cv2.boundingRect(c)
    row = dict(photo=name, corners=len(ids), rms_px=round(rms, 2),
               box_w_mm=round(bw_ / PPM, 2), box_h_mm=round(bh_ / PPM, 2),
               area_mm2=round(cv2.contourArea(c) / PPM**2, 1),
               perim_mm=round(cv2.arcLength(c, True) / PPM, 1))
    # Rotation-independent sizes: min-area rectangle and Feret (caliper) widths over all angles.
    (_, _), (ra, rb), _ = cv2.minAreaRect(c)
    pts = c.reshape(-1, 2).astype(float) / PPM
    th = np.radians(np.arange(0, 180, 0.25))
    wid = np.ptp(pts @ np.vstack([np.cos(th), np.sin(th)]), axis=0)
    row.update(rect_long_mm=round(max(ra, rb) / PPM, 2), rect_short_mm=round(min(ra, rb) / PPM, 2),
               feret_max_mm=round(wid.max(), 2), feret_min_mm=round(wid.min(), 2),
               feret_max_deg=float(np.degrees(th[wid.argmax()])))
    np.save(OUT / f"{name}_contour_mm.npy", pts)
    rows.append(row); print(row)
    ov = win.copy(); cv2.drawContours(ov, [c], -1, (0, 255, 0), 2)
    cv2.rectangle(ov, (bx, by), (bx + bw_, by + bh_), (255, 0, 0), 1)
    cv2.imwrite(str(OUT / f"{name}_rect.jpg"), ov)
(OUT / "measurements.json").write_text(json.dumps(rows, indent=1))
if rows:
    for k in ("box_w_mm", "box_h_mm", "rect_long_mm", "rect_short_mm", "feret_max_mm", "feret_min_mm", "area_mm2"):
        v = np.array([r[k] for r in rows])
        print(f"{k}: mean {v.mean():.2f}  std {v.std():.2f}  range {v.min():.2f}-{v.max():.2f}")
