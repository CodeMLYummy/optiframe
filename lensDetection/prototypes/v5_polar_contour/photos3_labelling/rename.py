# Record: ran once on 2026-10-04 against the ORIGINAL camera names in results_session3/ (before the rename),
# to label photos3 and write the index.csv files. Kept to document how the labels were made, not to re-run.
"""Rename the LFS photos to <lens>_<sheet>_<YYYYMMDD-HHMMSS>.jpg (git mv) and write an index.csv per folder."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
LD = HERE.parent  # lensDetection/
sys.path.insert(0, str(LD / "prototypes/v4_clear_lens"))
sys.path.insert(0, str(LD / "prototypes/v3_segmenter_tuning"))
sys.path.insert(0, str(HERE))
import seg_clear  # noqa: E402
from label import exif  # noqa: E402  (also re-runs nothing: label.py work is guarded below)

DRY = "--dry" in sys.argv

# Sheet labels checked by eye where the automatic label was missing or wrong (see contact sheets).
EYE = {
    "004555": "ronchi",
    "004558": "ronchi",
    "004604": "charuco-ronchi",
    "004608": "charuco-ronchi",
    "004736": "charuco-blank",
    "004757": "charuco-ronchi",
    "005203": "ronchi",
    "005204": "ronchi",
    "005207": "ronchi",
    "005304": "ronchi",
    "005323": "charuco-ronchi",
    "005355": "ronchi",
    "005356": "ronchi",
    "005408": "charuco-blank",
    "005410": "charuco-blank",
    "005437": "ronchi",
    "005457": "charuco-blank",
    "005450": "charuco-blank",
    "004734": "charuco-blank",
    "004857": "charuco-ronchi",
    "004542": "charuco-blank",
    "004752": "charuco-ronchi",
    "005231": "charuco-ronchi",
    "004544": "charuco-blank",
    "005407": "charuco-blank",
    "004706": "charuco-ronchi",
}


def git_mv(src: Path, dst: Path):
    if src == dst:
        return
    if DRY:
        print(f"  {src.name} -> {dst.name}")
    else:
        subprocess.run(["git", "mv", str(src), str(dst)], check=True, cwd=LD.parent)


def write_index(folder: Path, rows, fields):
    with open(folder / "index.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ---- photos3: two clear lenses
labels = {x["original"]: x for x in json.loads((HERE / "labels.json").read_text())}
rows = []
for orig, lab in sorted(labels.items()):
    key = orig[9:15]
    sheet, sheet_src = (EYE[key], "eye") if key in EYE else (lab["sheet"], "auto")
    long_mm = short_mm = ""
    win = HERE / "windows" / f"win_{orig[9:-4]}.png"
    if sheet == "charuco-blank" and win.exists():
        d = seg_clear.dims(seg_clear.v5(cv2.imread(str(win))))
        if isinstance(d, tuple):
            long_mm, short_mm = round(d[0], 2), round(d[1], 2)
    if short_mm != "":
        lens, lens_src = ("lens1" if short_mm < 35 else "lens2"), "measured"
    else:
        lens, lens_src = ("lens1" if key < "005100" else "lens2"), "time"
    stamp = "20261004-" + orig[9:15] + ("-2" if "(0)" in orig else "")
    new = f"{lens}_{sheet}_{stamp}.jpg"
    rows.append(
        dict(
            file=new,
            original=orig,
            lens=lens,
            lens_source=lens_src,
            sheet=sheet,
            sheet_source=sheet_src,
            chessboard_corners=lab["corners"],
            aruco_markers=lab["markers"],
            tilt_deg=lab.get("tilt_deg", ""),
            zoom=lab["zoom"],
            focal_35mm=lab["focal35"],
            v5_long_mm=long_mm,
            v5_short_mm=short_mm,
        )
    )
print("photos3:", len(rows), "files,", len({r["file"] for r in rows}), "unique names")
assert len({r["file"] for r in rows}) == len(rows)
for r in rows:
    git_mv(LD / "photos3" / r["original"], LD / "photos3" / r["file"])
write_index(LD / "photos3", rows, list(rows[0]))

# ---- photos2: red-tinted lens (sheet known from the session)
rows = []
for f in sorted((LD / "photos2").glob("20261003_*.jpg")):
    t = f.stem[9:]
    sheet = "charuco-blank" if t <= "212025" else ("ronchi" if t == "212145" else "charuco-ronchi")
    new = f"red_{sheet}_20261003-{t}.jpg"
    rows.append(dict(file=new, original=f.name, lens="red", sheet=sheet, taken=exif(f).get(0x9003, "")))
    git_mv(f, f.with_name(new))
print("photos2:", len(rows))
if rows:
    write_index(LD / "photos2", rows, list(rows[0]))

# ---- photos1: clear lens on a ChArUco board shown on a monitor (Pixel), plus the board alone
rows = []
for f in sorted((LD / "photos1").glob("*.jpg")):
    if f.name.startswith("PXL_"):
        stamp = f.name[4:12] + "-" + f.name[13:19]
        new, lens = f"clear0_screen-charuco_{stamp}.jpg", "clear0"
    elif f.name.startswith("charuto"):
        taken = exif(f).get(0x9003, "")
        stamp = taken.replace(":", "").replace(" ", "-")
        new, lens = f"nolens_screen-charuco_{stamp}.jpg", "none"
    else:
        continue
    rows.append(
        dict(
            file=new,
            original=f.name,
            lens=lens,
            sheet="screen-charuco (8x6, 4X4_50, on a monitor)",
            taken=exif(f).get(0x9003, ""),
        )
    )
    git_mv(f, f.with_name(new))
print("photos1:", len(rows))
if rows:
    write_index(LD / "photos1", rows, list(rows[0]))
