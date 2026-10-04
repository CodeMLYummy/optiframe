# Record: ran once on 2026-10-04 against the ORIGINAL camera names in results_session3/ (before the rename),
# to label photos3 and write the index.csv files. Kept to document how the labels were made, not to re-run.
"""Auto-label session-3 photos (sheet, tilt, zoom, backlight cue) for renaming; output checked by eye."""

import json
import struct
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "lensDetection/prototypes/v4_clear_lens"))
sys.path.insert(0, str(ROOT / "lensDetection/prototypes/v3_segmenter_tuning"))

L = json.loads((ROOT / "backend/src/main/resources/sheet-layout-charuco.json").read_text())
C, W = L["charuco"], L["lensWindow"]
d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, L["dictionary"]))
board = cv2.aruco.CharucoBoard((C["squaresX"], C["squaresY"]), C["squareMm"], C["markerMm"], d)
board.setLegacyPattern(C["legacyPattern"])
det = cv2.aruco.CharucoDetector(board)


def exif(path):
    t = open(path, "rb").read(200000)
    i = t.find(b"Exif\x00\x00")
    if i < 0:
        return {}
    t = t[i + 6 :]
    E = "<" if t[:2] == b"II" else ">"
    u16 = lambda o: struct.unpack(E + "H", t[o : o + 2])[0]
    u32 = lambda o: struct.unpack(E + "I", t[o : o + 4])[0]
    out = {}

    def ifd(o):
        for k in range(u16(o)):
            e = o + 2 + 12 * k
            tag, typ, cnt, val = u16(e), u16(e + 2), u32(e + 4), e + 8
            if typ == 2:
                s = t[u32(val) : u32(val) + cnt] if cnt > 4 else t[val : val + cnt]
                out[tag] = s.rstrip(b"\0").decode(errors="ignore")
            elif typ == 5:
                off = u32(val)
                out[tag] = u32(off) / max(1, u32(off + 4))
            elif typ == 3:
                out[tag] = u16(val)
            elif typ == 4:
                out[tag] = u32(val)

    ifd(u32(4))
    if 0x8769 in out:
        ifd(out[0x8769])
    return out


def periodic(profile, period_px):
    """Share of the profile's power near the stripe frequency (2 mm bars)."""
    p = profile - profile.mean()
    spec = np.abs(np.fft.rfft(p)) ** 2
    f = np.fft.rfftfreq(len(p))
    band = (f > 0.8 / period_px) & (f < 1.25 / period_px)
    return float(spec[band].sum() / max(spec[1:].sum(), 1e-9))


if __name__ == "__main__":
    rows = []
    for f in sorted((ROOT / "lensDetection/photos3").glob("*.jpg")):
        img = cv2.imread(str(f))
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ex = exif(f)
        h, w = g.shape
        corners, ids, _, mids = det.detectBoard(g)
        n = 0 if ids is None else len(ids)
        row = dict(
            original=f.name,
            corners=n,
            markers=0 if mids is None else len(mids),
            zoom=ex.get(0xA404),
            focal35=ex.get(0xA405),
            taken=ex.get(0x9003),
        )
        if n >= 8:
            obj = board.getChessboardCorners()[ids.ravel(), :2].astype(np.float32)
            img_pts = corners.reshape(-1, 2)
            H, _ = cv2.findHomography(obj, img_pts, cv2.RANSAC, 3.0)
            if H is None:  # corners found but degenerate (all on one line): no usable geometry
                row["sheet"] = "unknown"
                rows.append(row)
                print(json.dumps(row), flush=True)
                continue
            # Tilt: angle between the sheet normal and the camera axis, from H and the 35 mm-equivalent focal length.
            fpx = (row["focal35"] or 23) * np.hypot(w, h) / 43.27
            K = np.array([[fpx, 0, w / 2], [0, fpx, h / 2], [0, 0, 1]])
            M = np.linalg.inv(K) @ H
            r1, r2 = M[:, 0] / np.linalg.norm(M[:, 0]), M[:, 1] / np.linalg.norm(M[:, 1])
            r3 = np.cross(r1, r2)
            row["tilt_deg"] = round(float(np.degrees(np.arccos(abs(r3[2]) / np.linalg.norm(r3)))), 1)
            P = 5
            Hi, _ = cv2.findHomography(img_pts, obj * P, cv2.RANSAC, 3.0)
            rect = cv2.warpPerspective(img, Hi, (180 * P, 255 * P))
            x, y, ww, hh = (int(v * P) for v in (W["xMm"], W["yMm"], W["widthMm"], W["heightMm"]))
            win = rect[y + 15 : y + hh - 15, x + 15 : x + ww - 15]
            prof = cv2.cvtColor(win, cv2.COLOR_BGR2GRAY).astype(float).mean(axis=0)
            row["stripe_power"] = round(periodic(prof, 2 * P), 3)
            row["sheet"] = "charuco-ronchi" if row["stripe_power"] > 0.2 else "charuco-blank"
            hsv = cv2.cvtColor(win, cv2.COLOR_BGR2HSV)
            row["window_sat"] = int(np.median(hsv[..., 1]))
            row["window_val"] = int(np.median(hsv[..., 2]))
        else:
            # No board: stripes across the centre of the image mean the Ronchi-only sheet.
            c = g[h // 3 : 2 * h // 3, w // 4 : 3 * w // 4].astype(float)
            best = 0.0
            for prof in (c.mean(axis=0), c.mean(axis=1)):
                spec = np.abs(np.fft.rfft(prof - prof.mean())) ** 2
                best = max(best, float(spec[3:].max() / max(spec[1:].sum(), 1e-9)))
            row["stripe_power"] = round(best, 3)
            row["sheet"] = "ronchi" if best > 0.15 else "unknown"
        rows.append(row)
        print(json.dumps(row), flush=True)
    (HERE / "labels.json").write_text(json.dumps(rows, indent=1))
