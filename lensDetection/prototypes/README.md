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

## Setup

All scripts run from `lensDetection/` with a plain venv (gitignored):

```bash
cd lensDetection
python3 -m venv .venv && .venv/bin/pip install numpy opencv-python
```

Outputs go to gitignored `lensDetection/results_*` folders.

### Photos

- `lensDetection/photos1/` (committed): 3 photos of a clear lens on a ChArUco board shown on a monitor
  (8×6 squares, `4X4_50`), no paper. Used by v0, v1, SAM.
- `lensDetection/photos2/` (committed, Git LFS): second session, 14 photos `20261003_212010.jpg` …
  `20261003_212145.jpg`, red-tinted lens on the printed OptiFrame ChArUco sheet
  (`training/make_charuco_sheet.py`, Letter), paper over a lit monitor. 7 blank window, 6 Ronchi window,
  1 Ronchi-only sheet. Used by v2, v3 and the backend runs. Camera originals (Samsung S22 Ultra, main
  camera 23 mm eq., 1×, 4000×1868, EXIF kept). A first pass used recompressed copies; results matched
  within 0.03 mm.

## v1 — rim line (`v1_rim_line/rim_proto.py`)

```bash
WEAK=20 .venv/bin/python prototypes/v1_rim_line/rim_proto.py results_rim photos1/*.jpg
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
.venv/bin/python rim_gt.py gt ../../photos1/*.jpg     # proxy ground truth (v1 outlines) into gt/
.venv/bin/python run_sam.py sam2t sam2s vitb           # writes results CSV + overlays/
.venv/bin/python summarize.py results.csv iou_fill,bnd_mean_px prompt=b_box
```

Tested with Python 3.14, torch 2.14.1+cpu, SAM 2.1 at commit `2b90b9f`. Licences: SAM 2 and
Segment Anything are Apache-2.0 — cite them in the README if used in the app.
