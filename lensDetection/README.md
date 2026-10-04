# Ronchi ruling

Launch a fullscreen black-and-white Ronchi ruling with 0.5 mm-wide bars:

```sh
uv run ronchi
```

The stripe width is calculated from the display's reported pixel dimensions and
physical width. Press `Esc` to exit; `f` toggles fullscreen. For precise
optical measurements, verify the displayed scale with a ruler because the
physical display size reported by the operating system may be inaccurate.

# ChArUco board

Launch a fullscreen ChArUco board (8 x 6 squares by default) with its pattern
information shown along the bottom:

```sh
uv run charuco
```

Pass the number of squares across and high as positional arguments. Square and
marker side lengths in millimeters and the ArUco dictionary remain options:

```sh
uv run charuco 10 7 --square-mm 25 --marker-mm 18 --dictionary 4X4_50
```

Press `Esc` to exit; `f` toggles fullscreen.
The board is rendered using the display's reported physical width so its
configured millimeter dimensions can be shown at scale. On Linux, the active
monitor's RandR geometry is preferred over Tk's whole-screen dimensions, which
may be a synthetic 96-DPI value under Xwayland. Verify that scale with a ruler;
monitor EDID dimensions can still be approximate. If the board cannot fit at
that scale, the window reports the required pixel dimensions rather than
silently shrinking it.

# Demo: photo to measurement

Run the whole pipeline (`glass-edges`, then `close-contour`, then `boxing`) on
one photo, with all outputs in one folder:

```sh
uv run demo photo.jpg charuco.example.json --output-dir results
```

It stops at the first step that fails.

# Glass edge detection

Detect candidate outlines of a flat-ish transparent object lying over a ChArUco
board using OpenCV:

```sh
uv run glass-edges photo.jpg board.example.json --output-dir results
```

The JSON describes the actual pattern, not the image dimensions:

```json
{
  "squares_x": 8,
  "squares_y": 6,
  "square_mm": 25.0,
  "marker_mm": 18.0,
  "dictionary": "4X4_50"
}
```

Use the same values as the `charuco` generator. Square counts must be at least
3 in each direction. Lengths are in millimeters; the marker must be smaller
than its square. The dictionary name omits OpenCV's `DICT_` prefix. This assumes
the generator's default marker IDs and board layout. Verify the printed or
displayed physical scale with a ruler.

Keep the entire glass outline inside the board, leave at least six detectable
ChArUco corners spanning both directions uncovered, and use sharp, evenly lit
photos with at least about 12 pixels per square. A visible rim, reflection,
shadow, tint, or pattern distortion is necessary: perfectly clear glass with
no visible optical effect cannot be detected from an image alone.

The detector works in four steps:

1. **High-pass**: the photo minus a heavy blur, amplified, so thin details such
   as a glass rim stand out (`highpass.png`).
2. **Hough circle transform**: finds the round shape over the board. The
   board's own printed edges are removed from the Canny edges first so they do
   not win the vote: an edge pixel is erased only if it lies near an edge of the
   board rendered from the JSON (a margin absorbs drift) _and_ runs along one of
   the board's two axes, so a rim crossing a printed edge at an angle survives; the best circle is the one whose ring has edges all
   the way around.
3. **Canny edges isolated to the round edge**: only edges within `--tolerance`
   of the circle's radius are kept as the starting set (`edges.png`).
4. **Ellipse**: an ellipse is fitted to those edges over a few passes, each
   keeping a narrower ring around the previous fit, so stray edges stop pulling
   it. The final ellipse is the outline, and `edges.png` keeps only the edges
   on it. Gaps where the rim crosses a printed edge do not matter.

The glass need not be a perfect circle (spectacle lenses are not); the Hough
circle only locates it, and the ellipse gives the shape. `--tolerance` (default
0.3 of the circle's radius) is the initial ring width.
`--min-radius-mm` / `--max-radius-mm` bound the circle search (defaults: 0.4
board squares to half the board's short side). The minimum enclosed area
(`--min-area-mm2`) defaults to one board square.

The output directory contains `overlay.png` (Hough circle in orange, isolated
edges in red, fitted ellipse outline in green), `mask.png` (filled outline), `highpass.png`,
`edges.png` (Canny edges isolated to the ellipse), and `detections.json`
(Hough circle, fitted ellipse, pixel contour, board-plane contour in millimeters, area,
perimeter, and alignment diagnostics). Board coordinates start at the
board's top-left outer corner, with x rightward and y downward. Measurements
are **board-plane projections**, not corrected dimensions of raised or curved
glass. Use an undistorted image for measurement; camera lens distortion, glare,
shadows, poor registration, and large glass coverage can produce false
candidates. Suppression of printed edges also removes glass evidence where
the two overlap. This is a heuristic detector, not a guarantee of a complete
or exact glass boundary.

Exit status is 0 when candidates are found, 1 when none are found (diagnostic
outputs are still written), and 2 for invalid inputs or processing failures.
Existing output files are replaced, so use a separate directory per image.

## Closing the contour with a Bezier spline

The isolated rim edges usually have gaps where the rim crosses a printed edge.
`close-contour` reads a `glass-edges` output folder (`edges.png` and the fitted
ellipse in `detections.json`) and closes the rim with a cubic Bezier spline:

```sh
uv run glass-edges photo.jpg board.example.json --output-dir results/photo
uv run close-contour results/photo --image photo.jpg
```

The rim is cut into `--knots` angular spans (default 48) measured relative to
the fitted ellipse; each span with edge pixels becomes a knot at the median edge
radius. Empty spans are interpolated across the gap, and a closed Catmull-Rom
spline is converted to cubic Bezier segments through all the knots. It writes
`closed.svg` (1 path, pixel units), `closed.json` (Bezier segments in pixels,
the sampled contour in board millimeters, area, perimeter, which segments were
bridged), `closed_mask.png`, `closed_overlay.png` (green: measured rim, blue: bridged
gaps, red: input edges; drawn on `--image` when given), and
`closed_highpass_overlay.png` (the same drawing on the folder's `highpass.png`).
Exit status is 1 when less than `--min-coverage` (default 0.5) of the rim was
measured, since the bridge would then be mostly a guess, and 2 on invalid input.
Bridged gaps follow the ellipse-like interpolation, so wide gaps can cut inside
or outside the real rim.

## Boxing measurement

`boxing` measures the lens with the boxing method: the closed contour is
enclosed in the smallest rectangle whose sides are parallel to a horizontal
datum line. The box width is the lens **length (A)** and its height the lens
**width (B)**. Run it on a folder where `glass-edges` and `close-contour` have
both written their results:

```sh
uv run boxing results/photo --image photo.jpg
```

The datum is the board's x axis (the board's top edge as printed), which is not
necessarily horizontal in the photo. Use `--angle DEGREES` to tilt the datum
for a lens whose horizontal is rotated on the board. Measurements are made on
the board plane in millimeters from `closed.json`'s contour, so perspective is
corrected. It writes `boxing.json` (A, B, A/B, box center, box corners and
contact points in board millimeters) and `boxing_overlay.png` (green: lens,
yellow: boxing rectangle and center, red: contact points, blue: A and B
dimension arrows). Use `--output-dir` to write elsewhere. Exit status is 2 on
invalid input.

# Ronchi glass edge detection

Use the separate Ronchi detector for glass over parallel black-and-white bars:

```sh
uv run ronchi-edges photo.jpg ronchi.example.json --output-dir results-ronchi
```

The JSON supplies a measured rectangle on the pattern plane and its four
corresponding image points:

```json
{
  "width_mm": 20.0,
  "height_mm": 15.0,
  "bar_width_mm": 0.5,
  "corners_px": [
    [0, 0],
    [800, 0],
    [800, 600],
    [0, 600]
  ]
}
```

**Replace the example measurements and coordinates for your photo.** Coordinates
are `[x, y]` pixels, ordered top-left, top-right, bottom-right, bottom-left in
pattern coordinates. Bars must run parallel to the rectangle's left and right
edges; rotate the point ordering for horizontal bars. All four points must lie
inside the image. The measured rectangle need not include the entire ruling,
but must contain the complete glass outline. `bar_width_mm` is the width of
**one** black or white bar, not a full black/white period; the existing `ronchi`
generator uses 0.5 mm bars. Both colors must have equal widths.

Unlike ChArUco, parallel bars cannot uniquely recover the pattern plane or
the scale along the bars. The four measured correspondences are therefore
required rather than inferred. An undistorted image and accurate physical
measurements are needed for meaningful millimeter output.

The script rectifies perspective, checks the observed bar spacing against the
JSON, estimates the bare pattern using a median along each bar, suppresses
printed stripe edges, and connects remaining residuals into candidate outlines.
Use at least eight bars and at least six camera pixels per bar. Without a
reference, **more than half the rows in every column must show the unaffected
pattern**; large objects or optical effects extending along entire bars can
be missed.

For larger coverage or a nonuniform background, provide a bare-pattern photo:

```sh
uv run ronchi-edges photo.jpg ronchi.example.json \
  --reference bare-pattern.jpg --threshold 25 --min-area-mm2 2
```

The reference must have identical image dimensions and the camera, pattern,
and focus must not move. It uses the same corner mapping; no automatic reference
registration is attempted. Only global exposure changes are compensated.
`--threshold` is a grayscale residual from 0 to 255 (exclusive; default 30).
`--min-area-mm2` defaults to 1. Lower thresholds increase false positives.

Outputs are `overlay.png` (numbered outlines), `mask.png` (filled candidates),
`edges.png` (candidate boundaries), `rectified.png`, `residual.png` (in rectified
coordinates), and `detections.json` with contours in original image pixels and
pattern-plane millimeters, areas, perimeters, and the coordinate transform.
The millimeter origin is the rectangle's top-left corner, x rightward and y
downward. These are plane projections, not corrections for glass height or
curvature. Exit codes are 0 for candidates, 1 for none (outputs still written),
and 2 for input or processing errors. Existing outputs are replaced.

Visible rims, reflections, tint, shadows, or local stripe distortion are needed.
Invisible glass cannot be recovered. This heuristic may miss weak or interrupted
edges, especially where they coincide with printed stripes; gap filling may
merge nearby objects. Lighting changes and shadows can produce false candidates,
and clipped contours are discarded. Candidate outlines are not guaranteed to
be exact glass boundaries.
