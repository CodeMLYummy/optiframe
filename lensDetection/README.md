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
configured millimeter dimensions can be shown at scale. Verify that scale with
a ruler; if the board cannot fit at that scale, the window reports the required
pixel dimensions rather than silently shrinking it.

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

For better background suppression, take a second photo without the glass,
preferably with the camera, focus, lighting, and board unchanged:

```sh
uv run glass-edges photo.jpg board.example.json \
  --reference bare-board.jpg --threshold 25 --min-area-mm2 100
```

The reference must have the same image dimensions; it is aligned using the
board. Without it, the expected pattern is rendered from the JSON. The detector
fits a robust board homography, matches black/white brightness levels, suppresses
printed edges, and connects remaining residuals into candidate contours.
`--threshold` is a grayscale difference between 0 and 255 (default 30);
lower values increase sensitivity and false positives. The minimum enclosed
area defaults to one board square. Morphological gap filling can merge nearby
objects or simplify their outlines.

The output directory contains `overlay.png` (numbered green outlines),
`mask.png` (filled candidate regions), `residual.png` (background difference),
`edges.png` (observed edges left after template matching removes the board's
own straight edges, leaving curved rims), and `detections.json` (pixel contours, board-plane contours in millimeters,
areas, perimeters, and alignment diagnostics). Board coordinates start at the
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
  "corners_px": [[0, 0], [800, 0], [800, 600], [0, 600]]
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