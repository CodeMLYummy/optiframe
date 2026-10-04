# Lens outline detection — research log

What we tried to measure a spectacle lens outline from a phone photo, what worked, what didn't, and what
we recommend next. Started 2026-10-03 with the review of Richard's `lensDetection/` package (commits
`2262257`..`9ce9a4e`). Prototype scripts (v0–v3, SAM) are in [`prototypes/`](prototypes/README.md); A1–A2 are changes to the app backend.

## Summary

- **Where we are:** the app backend now reads the printed ChArUco sheet (Letter or A4) and measures a
  tinted lens on real photos with an A/B spread of ~2 mm / ~0.8 mm (5 photos, handheld). The sheet →
  mm part is solid (fit error 0.17–0.29 mm). The open risks are **clear lenses** (no real photos on
  the blank sheet yet), **parallax on steep shots** (+4 mm), and **no caliper ground truth** yet.
- **Recommendation:** keep the backlit blank-window ChArUco sheet as the capture setup; get caliper
  values and clear-lens photos next; add a tilt check; then add SAM (box-prompted by the classical
  pipeline) and/or a small model trained on synthetic + own photos for the "Données et IA" points.
- **What the jury scores** (`consignes.pdf`): A and B of two real lenses vs caliper, full 30 pts at
  ≤ 1 mm mean abs error, 0 at 4 mm.

## Version history

| Ver. | Date | Where | Idea | Result |
|---|---|---|---|---|
| v0 | 10-03 | `src/lensdetection/glass_edges.py` (Richard) | Subtract the expected ChArUco pattern; glass = residual | ❌ 0/3 photos |
| v0b | 10-03 | same, `--reference` | Subtract a second photo instead | ❌ 0/2 — the "reference" also had the lens and the camera moved |
| v1 | 10-03 | `prototypes/v1_rim_line/` | Clear lens on checkerboard: detect the thin rim line, pick pieces forming one closed curve | ✅ 3/3 outlines (pixels only, convex hull) |
| SAM | 10-03 | `prototypes/sam_eval/` | Segment Anything with point / box / automatic prompts | ⚠️ box prompt only (IoU 0.96–0.98) |
| v2 | 10-03 | `prototypes/v2_colour_charuco/` | New printed ChArUco sheet + tinted lens by colour | ✅ 11/14, A 46.65 ± 0.77, B 56.69 ± 0.45 mm |
| A1 | 10-04 | `backend/.../Rectifier.java` (commit `c7382f8`) | App: read the ChArUco sheet (was: 8-marker A4 sheet only) | ✅ 11/14 rectified, fit error 0.17–0.29 mm |
| v3 → A2 | 10-04 | `prototypes/v3_segmenter_tuning/` → `backend/.../ClassicalSegmenter.java` (commit `a865b76`) | App: stop the classical segmenter leaking into the lens shadow | ✅ A spread 4.6 → 2.0 mm, B 57.2–57.7 mm (excl. steep shot) |

## Context

### Challenge brief (`consignes.pdf`)
- **Scoring:** A and B (boxing system, ISO 8624) of the jury's two lenses vs caliper: 30 pts if mean
  abs error ≤ 1 mm, down to 0 at 4 mm. Contour SVG 1:1 (5). Robustness across angles/lighting + a pair
  of glasses brought by the jury (10). Data & AI (15). Web app (15). Frame STL (10). Code (5).
  Presentation (10).
- Left and right lenses are photographed **separately**; the user picks the eye; the bridge is a
  setting (18 mm default). Nasal side faces the frame centre.
- The jury rebuilds our capture setup in < 2 min; no manual annotation of evaluation photos.
- < 30 s per pair on a mid-range phone; browser processing recommended, Python/Java server allowed.
- Must output: contour SVG 1:1, step-by-step images, clear error messages. Frame clearance 0.1–0.3 mm.
- The brief's own tip: a clear lens is seen by its **edge gradients**, not its brightness.

### Organiser guidance (Discord, 2026-10-03)
- ±0.5 mm on A, B and bridge is the ISO 12870 tolerance; the jury threshold is 1 mm on A and B.
- Validate against a caliper on real lenses.
- Scale/perspective from a known flat reference + homography — the ChArUco sheet does this.
- **Don't use point clouds / AR:** phone depth fails on transparent surfaces.

## What we tried, in detail

### v0 — background subtraction (`glass-edges`, Richard's package)
- Renders the expected ChArUco board through the fitted homography and flags pixels that differ.
- **0 candidates** on `005615746` / `005617784`; `005621479` fails earlier ("Could not reliably fit
  the board plane").
- **Why it fails** (traced on `005615746`): the lens is nearly plano, so the board seen through it is
  barely distorted — the **rim is the only real signal**. Misregistration/blur along every printed
  edge leaves residual lines as strong as the rim (90th pct residual 31 vs threshold 30; edges masked
  only ±1 px). The 51 px closing fuses rim + edge noise into one ~18 000 mm² blob touching the board
  border, which is discarded as "clipped". Widening the edge mask (9/17/25 px) didn't help.
- **v0b `--reference`:** using another lens photo as reference also gave 0 candidates. A reference
  must be **glass-free** from an **unmoved** camera; otherwise rim parallax, resampling blur and
  moving glare remain.
- Unit tests pass (18/19) only because they use synthetic images.

### v1 — rim line on the checkerboard
1. Top-hat + black-hat (15 px ellipse, half resolution) → thin-line response; step edges cancel.
2. Hysteresis threshold (weak 20 / strong 35), keep long sparse components.
3. Choose the subset of the 10 longest pieces that best fits one closed ellipse-like curve.
4. Outline = convex hull.

| Photo | Coverage | Result |
|---|---|---|
| 005615746 | 86 % | tight outline |
| 005617784 | 78 % | only at full resolution (marker cells < kernel at half res); lower-left gap cut by a chord |
| 005621479 | 94 % | tight outline |

Dead ends on the way: fixed thresholds (35) caught only the brightest rim parts; greedy grouping from
the longest piece picked half the rim; "largest enclosed hole" after dilation filled the lens interior.

### SAM evaluation
243 runs: SAM 2.1 tiny / small and SAM ViT-B × 10 prompt types × 3 resolutions on the 3 clear-lens
checkerboard photos (done by a sub-agent; reference = v1 outlines, a proxy, not caliper).

| Prompt | Result |
|---|---|
| Box around the lens (exact or 10 % loose) | **Works:** filled IoU 0.96–0.98, edge error 7–8 px mean (~0.45 mm on photo 1), ~20 px p95 (~1.2 mm) |
| Point at centre (± negative points) | **Fails:** selects the checker square under the point |
| Automatic mask generation | **Fails:** no lens mask, ~26 s |
| Box 25 % loose / shifted 10 % / 10 % tight | Unreliable (IoU 0.1–0.9) |

- The mask is ~90 % **the rim ring** — fill it to get the lens (same cue as the classical method).
- SAM 2.1 tiny is as accurate as the larger models and fastest (~0.9 s/photo on CPU).
- **Verdict:** not usable alone; usable **seeded with an automatic box** from the classical pipeline.
  Not tried on the blank-window sheet (should be easier) nor deployed (ONNX Runtime Web / backend).

### v2 — printed ChArUco sheet, tinted lens by colour
Second session (`photos2/`, camera originals from the S22 Ultra, main camera 1×): 14 photos of a red-tinted lens on the printed sheet (`training/make_charuco_sheet.py`,
Letter, 12×17 × 15 mm squares, `DICT_5X5_250`, 120×165 mm lens window), paper over a lit monitor.
7 blank window, 6 Ronchi window, 1 Ronchi-only sheet.

- **11/14 measured.** Failures: 2 very oblique / cropped close-ups (no corners), the Ronchi-only sheet
  (no markers — expected).
- Same lens in every photo, so the spread is the repeatability:

  | | A (width) | B (height) | Min-area rect | Narrowest (Feret) |
  |---|---|---|---|---|
  | mean ± std | 46.65 ± 0.77 mm | 56.69 ± 0.45 mm | 56.27 × 46.68 mm | 46.51 ± 0.73 mm |

- The steepest shot (`212021`) is the largest: the ~2 mm lens side wall adds to the outline
  (parallax). Straight-down shots give ≈ 45.7 × 56.3 mm.
- Ronchi window: outline wobbles along bars (perimeter +~4 mm); box unaffected.
- **Doesn't match the supposed source frame** (Zenni aviator #451321: lens 54 × 37 mm). A 37 mm lens
  can't have a 46.5 mm minimum width, so rotation isn't the cause: probably a different lens, or the
  retailer spec is wrong. Print scaling could explain ~+4 % but not +26 %. → caliper the lens.
- Validates the sheet → mm part; colour segmentation itself only works for tinted lenses.
- Note: v2 and A1–A2 were first run on recompressed copies (no EXIF, ~350–600 KB). Re-run on the camera
  originals (2026-10-04): v2 gives A 46.56 ± 0.79, B 56.63 ± 0.47 mm; the backend gives the same A/B
  within 0.03 mm (steep shot `212021`: B −0.24 mm). The tables here keep the first-run values.

### A1 — app: ChArUco sheet in the rectifier
Before: the backend only loaded `sheet-layout.json` (A4, 8 markers `DICT_4X4_50`), so every photo of
the printed ChArUco sheet failed with "Feuille de référence introuvable". The old sheet doesn't fit on
Letter paper (bottom markers end at 285 mm).

- `optiframe.sheet-layout` selects the sheet; default `sheet-layout-charuco.json`
  (`OPTIFRAME_SHEET_LAYOUT=sheet-layout.json` for the old one).
- `Rectifier` fits the homography to ChArUco chessboard corners (sub-pixel, up to 68 outside the lens
  window; corners on the window edge are skipped); the rectified image covers the board, so Letter and
  A4 give identical results. Sharpness check uses the detected markers of either sheet.
- App links the Letter / A4 ChArUco PDFs; `docs/capture.md` updated.
- Real photos via `/api/measure`: 37–58 markers, fit error 0.17–0.29 mm, ~300 ms, same 3 failures as v2.
- Tests: `CharucoMeasurementServiceTest` (tilted synthetic photo within 0.3 mm, old sheet rejected);
  `MeasurementServiceTest` still covers the old sheet.

### v3 → A2 — app: shadow leak in the classical segmenter
- **Symptom:** after A1, blank-window photos measured A 46.4–51.0 mm (colour reference ≈ 46.7).
- **Cause:** the lens casts a soft shadow 15–30 grey levels darker than the paper, with a ~0.5 mm
  edge; the lens edge drops 80+ levels within a few pixels. The segmenter flagged anything 10 levels
  darker than its 3 mm neighbourhood and ran Canny 20/60, so it took the shadow as lens.
- **Fix:** darker-than-mean 25, Canny 40/100. Tuned on the real windows with a Python mirror: either
  change alone left the leak; both together brought 4/5 photos to a uniform ~+0.5 mm vs the colour
  mask.

  | Photo | Before A × B | After A × B |
  |---|---|---|
  | 212010 | 46.41 × 58.02 | 46.41 × 56.90 |
  | 212014 | 50.53 × 59.78 | 47.80 × 57.30 |
  | 212017 | 50.58 × 58.16 | 47.04 × 57.70 |
  | 212021 (steep) | 51.00 × 61.95 | 48.20 × 61.60 |
  | 212023 | 48.69 × 57.20 | 48.35 × 57.20 |

- **Remaining:** `212021` +4 mm on B is the lens's top face seen at a steep angle (parallax), not
  shadow. The ~+0.5–0.9 mm vs colour is likely the dark rim, to correct with `edge-bias-mm` once a
  caliper value exists.
- Tests: `ignoresTheSoftShadowNextToTheLens` (verified to **fail** on the old thresholds at 53.18 mm
  for a 50 mm lens) and `keepsAFaintRim` (a lighter, clear-lens-like rim still measures within 0.3 mm).

## Lessons

- **The rim is the signal.** A low-power clear lens barely distorts what's behind it; every working
  method (v1, SAM, the backend segmenter) finds the rim line, not the lens body.
- **A cluttered background is the enemy.** The checkerboard under the lens made every method fight
  printed edges. A blank, backlit window removes that problem — keep the pattern around the lens only.
- **Tune on real photos.** Synthetic tests passed for v0 and for the first version of the shadow test;
  only real photos showed the failures. Real-photo regression data should be kept (see To do).
- **Parallax is the biggest remaining error** on handheld photos: tilted shots add the lens side wall.
- **Consistent ≠ accurate:** v2 is repeatable to < 1 mm, but without a caliper value we don't know
  the bias.

## Recommendations

1. **Ground truth first:** caliper the red lens (A, B, longest and narrowest width) and check that 10
   printed squares measure 150 mm. Set `optiframe.edge-bias-mm` from the result.
2. **Clear lenses on the blank-window sheet**, shot from straight above. This is what the jury will
   test; re-tune `ClassicalSegmenter` with `prototypes/v3_segmenter_tuning/` if needed.
3. **Tilt check:** the homography gives the camera tilt; reject or warn above ~15° ("tenez le téléphone
   à plat"). Better later: model the rim height with a calibrated camera.
4. **Better error message** when the Ronchi sheet is used: "use the blank-window sheet", not
   "Verre introuvable".
5. **ML for "Données et IA" (15 pts):** SAM 2.1 tiny box-prompted by the classical box (no manual
   prompts), and/or a small model trained on synthetic images + own labelled photos (below). Report
   performance in mm against caliper values; cite every licence.
6. **Orientation (boxing system):** keep the alignment ticks + instruction; optionally let the user
   rotate the outline in the app.

## To do

- [ ] Caliper the red lens; check 10 squares = 150 mm; set `edge-bias-mm`.
- [ ] Photograph clear lenses on the blank-window sheet (straight down + a few tilted).
- [x] Commit the second photo session (`photos2/`, Git LFS), as camera originals.
- [ ] Tilt check in `MeasurementService`.
- [ ] Ronchi-sheet error message.
- [ ] **Generate synthetic training images.** Random lens shapes from the usual frame families (oval,
  rectangle, cat-eye, round, aviator, D-shape), rendered on a white backlit surface and on the
  checkerboard. Start with a **simple 2D image generator** (draw a grey/bright rim band and slightly
  shift the pattern inside the outline) before setting up full Blender rendering.
- [ ] SAM 2.1 tiny box-prompted, on the blank-window sheet; decide browser vs backend.
- [ ] Jury's own glasses (lenses may still be in the frame) — untested.
- [ ] Ask organisers whether a 3D printer is available (tiebreaker: print the frame, clip lenses in).
- [ ] Fill `docs/donnees-ia.md` "À compléter" (images, lenses, IoU, mm error).

## Approaches not tried yet

### Multiple shots with a fixed camera
Needs a phone stand. Through the paper diffuser, displayed stripe patterns blur out (no deflectometry),
but **white vs black screen** or **lens vs no lens** difference images still work: they cancel ambient
light, glare and paper texture. Lens power by deflectometry would need a separate capture without paper.

### Polarizer on the camera
LCDs emit polarized light; a polarizing film over the phone lens turns the screen black, and stressed
lens material (edging stress, especially polycarbonate) glows. Incompatible with the paper diffuser;
material-dependent → an extra cue, not a sole method. Cheapest experiment of all.

### Dark field
Black background, low-angle side light: the bevel glows, flat faces stay dark (commercial edge
scanners). Needs a light rig and separate scale markers.

### Improved rim fitting
Active contour / closed spline on the line response instead of a convex hull (smooth gaps, concave
nasal shapes); kernel sizes from the board's px/square.

## ML reference

### Dataset search (U-Net)
**No public dataset matches our setup** (edged lens alone on a backlit or patterned sheet). Eyewear
datasets show glasses on faces; glass datasets are scenes.

| # | Candidate | Licence | Size | Annotation | Relevance |
|---|---|---|---|---|---|
| 1 | [TransProteus](https://zenodo.org/records/5508261) + [generator](https://github.com/sagieppel/Procedural_Annotated_Images_Generation_Liquid_Transperent_Vessel) | MIT | 50k synthetic + 104 real | masks, depth, normals | Med — its Blender script is the best template for our own renderer |
| 2 | [Trans10K](https://github.com/xieenze/Segment_Transparent_Objects) | Apache, academic; commercial needs permission | 10,428 real | pixel masks | Low–Med — pretraining only |
| 3 | [ClearGrasp](https://github.com/Shreeyak/cleargrasp) | Apache-2.0 | 50k+ synthetic (72 GB) | masks, occlusion boundaries | Low–Med — boundary labels resemble our rim cue |
| 4 | [GDD / GDNet](https://github.com/Mhaiyang/CVPR2020_GDNet) | on application | 3,916 | glass masks | Low — building-scale glass |
| 5 | [Glasses Lenses Segmentation (Roboflow)](https://universe.roboflow.com/yair-etkes-iy1bq/glasses-lenses-segmentation) | not confirmed | ~172 | lens polygons | Low — on faces |
| 6 | [glasses-detector](https://github.com/mantasu/glasses-detector) | MIT code; mixed data | ~29k synthetic faces | frame/lens masks | Low — faces only |
| 7 | [lens_protocol](https://github.com/eeng/lens_protocol) (OMA/DCS traces) | MIT | 1 sample | radii trace → SVG | Tool only; no public trace collection exists |

Recommended path: procedural shapes r(θ) (box ~40–60 × 25–45 mm, nasal asymmetry) rendered on both
backgrounds (2D compositor first, Blender Cycles later), 5k–20k images with a lens mask and a thin rim
mask; ~150–300 own photos labelled with SAM assistance (CVAT / Label Studio, ~1–2 min each), ~50 held
out with caliper values; train on synthetic, fine-tune on real, report mm error. Ask an optician for a
few real `.oma` traces to validate the shapes. Check first whether the classical method already meets
the target on the backlit sheet.

## Accuracy recommendations (any approach)
- **Parallax:** shoot straight down, from farther away with zoom; correct for lens height if known.
- **Camera distortion:** calibrate the phone once with the ChArUco board and undistort.
- **Fixed stand:** biggest single gain in repeatability.
- **Ground truth:** calipers or a known template shape; report mm error, not just overlays.
- **Glare:** dim room lights, tilt slightly off the screen's reflection axis.

## Housekeeping found in the review (Richard's package)
- `test_board_json_validation` fails: `load_board` raises `TypeError` instead of `ValueError`.
- Default `--output-dir` `results_<datetime.now()>` has spaces/colons → `strftime("%Y%m%d-%H%M%S")`;
  unused `timezone` import.
- README references `board.example.json` (renamed `charuco.example.json`).
- ~21 MB of photos committed in `photos1/` (consider Git LFS).
- `ronchi-edges` default output dir is not gitignored.
- Placeholders: empty `lens_detection.py`, hello-world entry point, `echantillon.md`, pyproject
  description.
- `charuco` generator accepts 2×2 boards but `load_board` requires ≥ 3×3.
