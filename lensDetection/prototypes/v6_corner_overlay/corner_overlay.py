"""v6: overlay the sub-pixel ChArUco corner detection on every photo of the bank (diagnostic, no measurement).

For each photo: the chessboard corners the detector finds (sub-pixel cross), coloured by role (used for the
homography / skipped on the lens-window edge), the corners the board has but that were not found, each inlier's
reprojection error after the RANSAC homography fit (arrow x20; rejected corners as red squares), the projected lens window, the detected ArUco markers,
x8 insets of a few corners, and a stats line. Numbers are raw: no print-scale or edge correction.

usage (from lensDetection/): .venv/bin/python prototypes/v6_corner_overlay/corner_overlay.py [photos1 photos2 photos3]
Writes results_v6/<folder>/<photo>.jpg, results_v6/<folder>/contact.jpg and results_v6/corners.csv (gitignored).
"""

import csv
import json
import struct
import sys
from pathlib import Path

import cv2
import numpy as np

LD = Path(__file__).resolve().parents[2]
OUT = LD / "results_v6"

GREEN = (60, 220, 60)  # detected, used for the homography
ORANGE = (0, 165, 255)  # detected, on the lens-window edge (skipped by the backend)
RED = (40, 40, 230)  # expected by the board but not detected
BLUE = (255, 160, 40)  # ArUco markers
YELLOW = (0, 230, 255)  # projected lens window
MAGENTA = (255, 0, 255)  # reprojection error arrows (inliers)
OUTLIER = (0, 0, 255)  # detected but rejected by RANSAC (blur, misdetection, paper not flat)
ARROW = 20  # reprojection error magnification


def printed_sheet():
    layout = json.loads((LD.parent / "backend/src/main/resources/sheet-layout-charuco.json").read_text())
    c = layout["charuco"]
    board = cv2.aruco.CharucoBoard(
        (c["squaresX"], c["squaresY"]),
        c["squareMm"],
        c["markerMm"],
        cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, layout["dictionary"])),
    )
    board.setLegacyPattern(c["legacyPattern"])
    return "OptiFrame ChArUco 12x17 (printed)", board, layout["lensWindow"]


def screen_board():
    c = json.loads((LD / "charuco.example.json").read_text())
    board = cv2.aruco.CharucoBoard(
        (c["squares_x"], c["squares_y"]),
        c["square_mm"],
        c["marker_mm"],
        cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, "DICT_" + c["dictionary"])),
    )
    return "ChArUco 8x6 on a monitor", board, None


BOARDS = {"photos1": screen_board, "photos2": printed_sheet, "photos3": printed_sheet}


def exif_camera(path):
    """(35 mm-equivalent focal, digital zoom) from EXIF, or (None, None)."""
    t = open(path, "rb").read(200000)
    i = t.find(b"Exif\x00\x00")
    if i < 0:
        return None, None
    t = t[i + 6 :]
    E = "<" if t[:2] == b"II" else ">"
    u16 = lambda o: struct.unpack(E + "H", t[o : o + 2])[0]
    u32 = lambda o: struct.unpack(E + "I", t[o : o + 4])[0]
    out = {}

    def ifd(o):
        for k in range(u16(o)):
            e = o + 2 + 12 * k
            tag, typ, val = u16(e), u16(e + 2), e + 8
            if typ == 3:
                out[tag] = u16(val)
            elif typ == 4:
                out[tag] = u32(val)
            elif typ == 5:
                off = u32(val)
                out[tag] = u32(off) / max(1, u32(off + 4))

    try:
        ifd(u32(4))
        if 0x8769 in out:
            ifd(out[0x8769])
    except struct.error:
        pass
    return out.get(0xA405), out.get(0xA404)


def on_window_edge(p, window, margin=0.5):
    if window is None:
        return False
    x, y = p
    return (
        window["xMm"] - margin <= x <= window["xMm"] + window["widthMm"] + margin
        and window["yMm"] - margin <= y <= window["yMm"] + window["heightMm"] + margin
    )


def inset(img, center, scale=8, half=12):
    """x`scale` crop around a sub-pixel point, with the point marked exactly."""
    x, y = center
    x0, y0 = int(round(x)) - half, int(round(y)) - half
    h, w = img.shape[:2]
    if x0 < 0 or y0 < 0 or x0 + 2 * half + 1 > w or y0 + 2 * half + 1 > h:
        return None
    crop = cv2.resize(
        img[y0 : y0 + 2 * half + 1, x0 : x0 + 2 * half + 1], None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST
    )
    cx, cy = (x - x0 + 0.5) * scale, (y - y0 + 0.5) * scale  # pixel centres sit at +0.5 in the zoomed grid
    cv2.drawMarker(crop, (int(round(cx)), int(round(cy))), GREEN, cv2.MARKER_CROSS, 3 * scale, 2)
    cv2.circle(crop, (int(round(cx)), int(round(cy))), scale, GREEN, 1, cv2.LINE_AA)
    cv2.rectangle(crop, (0, 0), (crop.shape[1] - 1, crop.shape[0] - 1), (255, 255, 255), 2)
    return crop


def analyse(path, board, window, detector):
    img = cv2.imread(str(path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, marker_corners, marker_ids = detector.detectBoard(gray)
    board_corners = board.getChessboardCorners()[:, :2].astype(np.float32)
    n_expected = sum(not on_window_edge(p, window) for p in board_corners) if window else len(board_corners)
    ov = img.copy()
    lw = max(2, img.shape[1] // 900)
    focal, zoom = exif_camera(path)
    stats = dict(
        photo=path.name,
        corners_found=0,
        corners_used=0,
        corners_expected=n_expected,
        markers=0 if marker_ids is None else len(marker_ids),
        outliers="",
        rms_px="",
        max_px="",
        focal_35mm=focal or "",
        zoom=zoom or "",
    )
    if marker_corners:
        cv2.aruco.drawDetectedMarkers(ov, marker_corners, None, BLUE)
    if ids is None or len(ids) < 4:
        return ov, stats, []

    ids = ids.ravel()
    pts = corners.reshape(-1, 2)
    obj = board_corners[ids]
    used = np.array([not on_window_edge(p, window) for p in obj])
    stats.update(corners_found=len(ids), corners_used=int(used.sum()))
    H, inl = cv2.findHomography(obj[used], pts[used], cv2.RANSAC, 3.0) if used.sum() >= 4 else (None, None)
    if H is not None:
        proj = cv2.perspectiveTransform(obj[None], H)[0]
        err = pts - proj
        # Statistics over the RANSAC inliers, as the backend fits; outliers are counted and drawn apart.
        inlier = np.zeros(len(pts), bool)
        inlier[np.flatnonzero(used)[inl.ravel() > 0]] = True
        e = np.linalg.norm(err[inlier], axis=1)
        stats.update(
            outliers=int(used.sum() - inlier.sum()),
            rms_px=round(float(np.sqrt(np.mean(e**2))), 3),
            max_px=round(float(e.max()), 3),
        )
        # Corners the board has but the detector missed, at their homography position.
        missing = np.setdiff1d(np.arange(len(board_corners)), ids)
        for k in missing:
            if on_window_edge(board_corners[k], window):
                continue
            q = cv2.perspectiveTransform(board_corners[k][None, None], H)[0, 0]
            if 0 <= q[0] < img.shape[1] and 0 <= q[1] < img.shape[0]:
                cv2.drawMarker(ov, (int(q[0]), int(q[1])), RED, cv2.MARKER_TILTED_CROSS, 6 * lw, lw)
        if window is not None:
            w = window
            quad = np.float32(
                [
                    [w["xMm"], w["yMm"]],
                    [w["xMm"] + w["widthMm"], w["yMm"]],
                    [w["xMm"] + w["widthMm"], w["yMm"] + w["heightMm"]],
                    [w["xMm"], w["yMm"] + w["heightMm"]],
                ]
            )
            cv2.polylines(ov, [cv2.perspectiveTransform(quad[None], H)[0].astype(np.int32)], True, YELLOW, lw)
    else:
        err = np.zeros_like(pts)
        inlier = np.zeros(len(pts), bool)
    for p, e_vec, u, ok in zip(pts, err, used, inlier):
        c = (int(round(p[0])), int(round(p[1])))
        if u and not ok:
            cv2.drawMarker(ov, c, OUTLIER, cv2.MARKER_SQUARE, 8 * lw, lw)
            continue
        cv2.circle(ov, c, 4 * lw, GREEN if u else ORANGE, lw, cv2.LINE_AA)
        if ok:
            tip = (int(round(p[0] + ARROW * e_vec[0])), int(round(p[1] + ARROW * e_vec[1])))
            cv2.arrowedLine(ov, c, tip, MAGENTA, lw, cv2.LINE_AA, tipLength=0.3)
    # Insets: corners closest to the top-left, right-middle and bottom of the detected set.
    picks = []
    for target in (
        pts.min(axis=0),
        np.array([pts[:, 0].max(), np.median(pts[:, 1])]),
        np.array([np.median(pts[:, 0]), pts[:, 1].max()]),
    ):
        picks.append(pts[np.argmin(np.linalg.norm(pts - target, axis=1))])
    insets = [i for i in (inset(img, tuple(p)) for p in picks) if i is not None]
    return ov, stats, insets


def compose(ov, stats, insets, title):
    h, w = ov.shape[:2]
    s = 1800 / max(h, w)
    small = cv2.resize(ov, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    if insets:
        strip = np.hstack(insets)
        k = min(1.0, small.shape[1] / strip.shape[1])
        strip = cv2.resize(strip, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
        pad = np.zeros((strip.shape[0], small.shape[1], 3), np.uint8)
        pad[:, : strip.shape[1]] = strip
        small = np.vstack([small, pad])
    bar = np.zeros((70, small.shape[1], 3), np.uint8)
    line1 = f"{stats['photo']}  |  {title}"
    line2 = (
        f"corners {stats['corners_used']} used ({stats['outliers']} outliers) + "
        f"{stats['corners_found'] - stats['corners_used']} on window edge / {stats['corners_expected']} expected"
        f"   markers {stats['markers']}   inlier RMS {stats['rms_px']} px  max {stats['max_px']} px"
        f"   cam {stats['focal_35mm']}mm x{stats['zoom']}   arrows x{ARROW}"
    )
    cv2.putText(bar, line1, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(bar, line2, (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 255, 200), 1, cv2.LINE_AA)
    return np.vstack([bar, small])


def contact(images, path, cols=6, width=300):
    th = []
    for im in images:
        s = width / im.shape[1]
        th.append(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    hmax = max(t.shape[0] for t in th)
    th = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 2, cv2.BORDER_CONSTANT) for t in th]
    while len(th) % cols:
        th.append(np.zeros_like(th[0]))
    cv2.imwrite(str(path), np.vstack([np.hstack(th[i : i + cols]) for i in range(0, len(th), cols)]))


def main():
    folders = sys.argv[1:] or ["photos1", "photos2", "photos3"]
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX  # as the backend's Rectifier
    rows = []
    for folder in folders:
        title, board, window = BOARDS[folder]()
        detector = cv2.aruco.CharucoDetector(board, cv2.aruco.CharucoParameters(), params)
        out = OUT / folder
        out.mkdir(parents=True, exist_ok=True)
        thumbs = []
        for f in sorted((LD / folder).glob("*.jpg")):
            ov, stats, insets = analyse(f, board, window, detector)
            page = compose(ov, stats, insets, title)
            cv2.imwrite(str(out / f.name), page, [cv2.IMWRITE_JPEG_QUALITY, 88])
            thumbs.append(page)
            rows.append(dict(folder=folder, **stats))
            print(
                f"{folder}/{f.name}: {stats['corners_used']}+{stats['corners_found'] - stats['corners_used']}"
                f"/{stats['corners_expected']} corners, {stats['outliers']} outliers, RMS {stats['rms_px']} px",
                flush=True,
            )
        if thumbs:
            contact(thumbs, out / "contact.jpg")
    with open(OUT / "corners.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
