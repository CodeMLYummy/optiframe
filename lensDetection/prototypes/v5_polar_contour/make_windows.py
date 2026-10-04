"""Rectify the lens window of every photos3 photo where the ChArUco board is found (10 px/mm, as the backend).

usage (from lensDetection/): .venv/bin/python prototypes/v5_polar_contour/make_windows.py
Writes results_session3/windows/win_<HHMMSS[-n]>.png (gitignored), the input of seg_clear.py.
"""

import json
from pathlib import Path

import cv2
import numpy as np

LD = Path(__file__).resolve().parents[2]
L = json.loads((LD.parent / "backend/src/main/resources/sheet-layout-charuco.json").read_text())
C, W = L["charuco"], L["lensWindow"]
board = cv2.aruco.CharucoBoard(
    (C["squaresX"], C["squaresY"]),
    C["squareMm"],
    C["markerMm"],
    cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, L["dictionary"])),
)
board.setLegacyPattern(C["legacyPattern"])
detector = cv2.aruco.CharucoDetector(board)
PPM = 10
EDGE_MM = 0.5  # corners on the window edge have no chessboard around them: skip them, as the backend does

out = LD / "results_session3" / "windows"
out.mkdir(parents=True, exist_ok=True)
n = 0
for f in sorted((LD / "photos3").glob("*.jpg")):
    img = cv2.imread(str(f))
    corners, ids, _, _ = detector.detectBoard(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    if ids is None or len(ids) < 8:
        continue
    obj = board.getChessboardCorners()[ids.ravel(), :2].astype(np.float32)
    outside = [
        not (
            W["xMm"] - EDGE_MM <= x <= W["xMm"] + W["widthMm"] + EDGE_MM
            and W["yMm"] - EDGE_MM <= y <= W["yMm"] + W["heightMm"] + EDGE_MM
        )
        for x, y in obj
    ]
    H, _ = cv2.findHomography(corners.reshape(-1, 2)[outside], obj[outside] * PPM, cv2.RANSAC, 3.0)
    if H is None:
        continue
    rect = cv2.warpPerspective(img, H, (int(180 * PPM), int(255 * PPM)))
    x, y, w, h = (int(v * PPM) for v in (W["xMm"], W["yMm"], W["widthMm"], W["heightMm"]))
    key = f.stem.split("_")[-1].split("-", 1)[1]  # lens1_charuco-blank_20261004-004540 -> 004540
    cv2.imwrite(str(out / f"win_{key}.png"), rect[y : y + h, x : x + w])
    n += 1
print(n, "windows in", out)
