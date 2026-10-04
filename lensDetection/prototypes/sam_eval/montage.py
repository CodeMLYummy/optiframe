"""Grid: rows = photos, cols = prompt modes (sam2t, full1024)."""

import sys

import cv2
import numpy as np
from common import HERE, NAMES

model = sys.argv[1] if len(sys.argv) > 1 else "sam2t"
modes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["a_point", "c_point+neg", "b_box", "f_rimclicks", "d_auto"]
rows = []
for n in NAMES:
    tiles = []
    for m in modes:
        p = HERE / "overlays" / f"{model}_{n}_full1024_{m}.jpg"
        im = cv2.imread(str(p))
        if im is None:
            im = np.zeros((384, 510, 3), np.uint8)
        im = cv2.resize(im, (510, 384))
        cv2.putText(im, f"{n} {m}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(im, f"{n} {m}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        tiles.append(im)
    rows.append(np.hstack(tiles))
cv2.imwrite(str(HERE / f"montage_{model}.jpg"), np.vstack(rows))
