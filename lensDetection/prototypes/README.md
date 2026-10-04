# Lens-detection prototypes

Throwaway-quality research scripts that informed the backend (`backend/.../vision/`). Each version is
frozen as it was when its results were recorded; the reasoning and results are in
[`../approaches.md`](../approaches.md).

| Version | Folder | Question it answered | Outcome |
|---|---|---|---|
| v0 | `../src/lensdetection/glass_edges.py` (Richard's package) | Can we find the lens by subtracting the expected checkerboard? | **No.** 0 candidates on all 3 clear-lens photos: printed-edge misregistration is as strong as the rim |
| v1 | `v1_rim_line/` | Can we find a clear lens by its thin rim line on the checkerboard? | **Yes, roughly.** Top-hat/black-hat + ellipse-consistent piece selection finds the rim on 3/3 photos; convex hull, pixels only |
| v2 | `v2_colour_charuco/` | Does the printed ChArUco sheet give reliable mm? (tinted lens, colour segmentation) | **Yes.** 11/14 photos, A 46.65 ± 0.77, B 56.69 ± 0.45 mm (same lens) |
| v3 | `v3_segmenter_tuning/` | Why does the backend's classical segmenter over-measure? | Shadow leak; fixed with Canny 40/100 + darker-than-mean 25 (ported to Java) |
| SAM | `sam_eval/` | Can Segment Anything outline the lens? | Only with a box prompt (filled IoU 0.96–0.98); points and automatic mode fail |
| v4 | `v5_polar_contour/seg_clear.py` (`v4`) | Clear lenses on the blank window: close the rim ring and fill it? | **No.** 3–10 / 34: the faint rim has gaps and cables touch it, so the fill fails or floods |
| v7–v9 | `v7_v8_v9_detector/` | Do ChArUco detector settings (`minMarkers=1`, `tryRefineMarkers`, both) help end to end? | Coverage, not accuracy: measured 37 → 40 / 41 / 40 of 54; MAE on common photos unchanged (0.81–0.83 mm). v8 (`tryRefineMarkers`) best; v7/v9 trip the fold check |
| v6 | `v6_corner_overlay/` | Diagnostic: how good is the sub-pixel ChArUco corner detection on every photo? | Detection is sharp (×8 insets) but the sheet isn't a plane: inlier RMS ~1.4 px, outliers on 64 / 67 photos (blur, curl); side columns found 42–55 % vs 70–75 % for top/bottom rows |
| v5 | `v5_polar_contour/` | Clear lenses: best closed path r(θ) around the centre (polar contour, dynamic programming)? | **Yes.** 28 / 34 blank windows (backend today: 7); lens 1 50.18 ± 0.99 × 31.33 ± 0.98, lens 2 51.51 ± 0.64 × 38.20 ± 0.48 mm; red lens within 0.8 mm of its colour mask |

## Setup

All scripts run from `lensDetection/` with a plain venv (gitignored):

```bash
cd lensDetection
python3 -m venv .venv && .venv/bin/pip install numpy opencv-python
```

Outputs go to gitignored `lensDetection/results_*` folders.

### Photos

All photos are in Git LFS, named `<lens>_<sheet>_<YYYYMMDD-HHMMSS>.jpg` (camera time kept), with an
`index.csv` per folder (original name, labels, and for `photos3` tilt, zoom and v5 measurements).
Lenses: `clear0` (session 1), `red`, `lens1` / `lens2` (session 3, clear), `nolens`. Sheets: `screen-charuco`
(board on a monitor), `charuco-blank`, `charuco-ronchi`, `ronchi` (Ronchi-only, no markers).

- `lensDetection/photos1/`: 3 photos of a clear lens on a ChArUco board shown on a monitor
  (8×6 squares, `4X4_50`), no paper, plus the board alone. Used by v0, v1, SAM.
- `lensDetection/photos2/`: second session, 14 photos `red_*_20261003-212010.jpg` …
  `red_ronchi_20261003-212145.jpg`, red-tinted lens on the printed OptiFrame ChArUco sheet
  (`training/make_charuco_sheet.py`, Letter), paper over a lit monitor. 7 blank window, 6 Ronchi window,
  1 Ronchi-only sheet. Used by v2, v3 and the backend runs. Camera originals (Samsung S22 Ultra, main
  camera 23 mm eq., 1×, 4000×1868, EXIF kept). A first pass used recompressed copies; results matched
  within 0.03 mm.

## v1 — rim line (`v1_rim_line/rim_proto.py`)

```bash
WEAK=20 .venv/bin/python prototypes/v1_rim_line/rim_proto.py results_rim photos1/clear0_*.jpg
```

1. Top-hat + black-hat (15 px ellipse at half resolution): responds to thin lines, cancels step edges.
2. Hysteresis threshold (weak `WEAK`, strong 35) and keep long, sparse components.
3. Try subsets of the 10 longest pieces; keep the one that best fits a single closed ellipse-like
   curve (max angular coverage, rms ≤ 0.06).
4. Outline = convex hull. `SCALE=1.0` is needed when the board is small in the frame.

Known limits: kernel size not scaled to the board, convex-hull assumption, straight chords across gaps,
pixels only.

## v2 — colour on the ChArUco sheet (`v2_colour_charuco/red_proto.py`)

```bash
.venv/bin/python prototypes/v2_colour_charuco/red_proto.py photos2/*.jpg
```

ChArUco detection with the sheet layout from `backend/src/main/resources/sheet-layout-charuco.json` →
RANSAC homography → rectify at 10 px/mm → Lab a\* (redness vs paper) + Otsu → close 2.5 mm (bridges
Ronchi bars) → largest contour. Reports axis box, min-area rectangle and Feret widths; saves the contour
in mm (`*_contour_mm.npy`) and `measurements.json`. **Tinted lenses only.**

## v3 — classical segmenter tuning (`v3_segmenter_tuning/seg_lab.py`)

Python mirror of `ClassicalSegmenter.java`, scored against the colour mask of the red lens (A/B error,
IoU, worst outward leak). Input windows come from the backend itself:

```bash
# 1. capture the rectified windows the backend sees
cd backend && OPTIFRAME_DATASET_DIR=$PWD/../lensDetection/results_seg/dataset ./mvnw spring-boot:run
#    POST each photo to /api/measure, then copy dataset/images/*.png to results_seg/win_<photo>.png
# 2. compare threshold variants
cd lensDetection && .venv/bin/python prototypes/v3_segmenter_tuning/seg_lab.py
```

## v5 — polar contour for clear lenses (`v5_polar_contour/`)

```bash
.venv/bin/python prototypes/v5_polar_contour/make_windows.py   # photos3 -> results_session3/windows/
.venv/bin/python prototypes/v5_polar_contour/seg_clear.py      # table + overlays in results_session3/v5/
```

1. Rim map: black-hat + top-hat (~1.6 mm) answers to the thin rim, not to wide soft shadows; divided by
   the photo's own background level (90th percentile), so backlit paper texture and smooth paper compare.
2. Seed the centre at the median of the strongest line pixels.
3. `warpPolar` around the centre: 720 angles (0.5°) × radius 0–45 mm (8 mm minimum), values capped at 6
   so one glare spot can't outweigh a faint rim.
4. Dynamic programming over two turns: the closed path r(θ) with the most rim evidence, ≤ 0.4 mm radius
   change per 0.5°, and a cost of 0.4 per pixel of change (detours to cables must pay).
5. Re-centre on the found loop, run once more; fill the loop as the mask.
6. Refuse (lens not found) when the path sits on rim evidence along < 50 % of its length (`MIN_RIM`).

`seg_clear.py` also keeps `v4` (ring fill) as the documented failed attempt, and runs the backend's current
logic (`v3_segmenter_tuning/seg_lab.py`) for comparison. Remaining misses: 3 unlit warm-light photos (below
the 50 % evidence rule), 1 degenerate rectification, 1 lens on the window edge, 1 striped window. Limits:
star-shaped outlines only; on steep shots the path can take the lens's top edge (parallax).

`photos3_labelling/` holds the one-off scripts that labelled and renamed `photos3` and wrote the
`index.csv` files; they ran on the original camera names and are kept as a record, not to re-run.

## v6 — corner detection overlay (`v6_corner_overlay/`)

```bash
.venv/bin/python prototypes/v6_corner_overlay/corner_overlay.py            # all of photos1-3
```

Diagnostic only, numbers left raw (no print-scale or edge correction). One overlay per photo in
`results_v6/<folder>/` (plus `contact.jpg`) and `results_v6/corners.csv`: detected chessboard corners (sub-pixel
cross; green = used for the homography, orange = on the lens-window edge, skipped like the backend), RANSAC
outliers (red squares), board corners not found (red ×, at their fitted position), each inlier's reprojection error
(magenta arrow ×20), the projected lens window, detected markers, ×8 insets of three corners, and a stats line
(corners used / outliers / expected, inlier RMS, camera). Board per folder: the printed 12×17 sheet for
`photos2`/`photos3`, the 8×6 screen board for `photos1`.

## v7–v9 — ChArUco detector settings (`v7_v8_v9_detector/`)

```bash
.venv/bin/python prototypes/v7_v8_v9_detector/measure.py
```

Runs the full backend pipeline in Python (Rectifier rules incl. the 0.5 mm fold check, lens window, v5 with
snap, ContourMeasurer's smoothed sheet-axis A × B) on the 54 blank-window photos with a caliper-measured lens,
for four detector settings: base (today), v7 `minMarkers=1`, v8 `tryRefineMarkers`, v9 both. Scores raw and at
the true print scale (73.4 / 75). Per-photo results in `results_v7_v9/measurements.csv`.

| Variant | Measured | MAE (true scale) | Fold-check failures |
|---|---|---|---|
| base | 37 / 54 | 0.84 mm | 1 |
| v7 | 40 / 54 | 0.80 mm | 2 |
| v8 | 41 / 54 | 0.80 mm | 0 |
| v9 | 40 / 54 | 0.81 mm | 2 |

The fold check averages the error over all corners, RANSAC outliers included; single-marker corners (v7, v9)
add outliers and trip it. On the 36 photos all variants measure, MAE is 0.81–0.83 mm for every setting.

`pictures.py` renders, for the photos v8 rescues (or any given photos), base vs v8 corner detection (v6 overlay)
and the lens outline v8 measures with its error against the caliper, into `results_v7_v9/v8_pictures/`.

## SAM evaluation (`sam_eval/`)

Written by a sub-agent in an isolated worktree; `results.csv` holds all 243 runs (3 models × 10 prompts ×
3 resolutions × 3 photos). Reference masks are v1 outlines (a proxy, not caliper truth).

```bash
cd lensDetection/prototypes/sam_eval
python3 -m venv .venv && .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install opencv-python-headless numpy segment_anything
git clone https://github.com/facebookresearch/sam2.git sam2src   # tested at 2b90b9f
.venv/bin/pip install -e sam2src
mkdir ckpt   # download into ckpt/:
#   sam2.1_hiera_tiny.pt, sam2.1_hiera_small.pt  (https://dl.fbaipublicfiles.com/segment_anything_2/092824/)
#   sam_vit_b_01ec64.pth                         (https://dl.fbaipublicfiles.com/segment_anything/)
.venv/bin/python rim_gt.py gt ../../photos1/clear0_*.jpg     # proxy ground truth (v1 outlines) into gt/
.venv/bin/python run_sam.py sam2t sam2s vitb           # writes results CSV + overlays/
.venv/bin/python summarize.py results.csv iou_fill,bnd_mean_px prompt=b_box
```

Tested with Python 3.14, torch 2.14.1+cpu, SAM 2.1 at commit `2b90b9f`. Licences: SAM 2 and
Segment Anything are Apache-2.0 — cite them in the README if used in the app.
