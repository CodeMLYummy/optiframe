# Photo session 3 — clear lenses (2026-10-04, 00:45–00:55)

119 camera originals (Samsung Galaxy S22 Ultra, EXIF kept), pulled from the phone over adb, named
`<lens>_<sheet>_<YYYYMMDD-HHMMSS>.jpg`. [`index.csv`](index.csv) lists each photo's original name, lens and
sheet (and whether that label was automatic or checked by eye), tilt, zoom and the v5 prototype's
measurement.

- **Lenses:** two clear (untinted) lenses of different shapes, not yet measured with a caliper:
  - `lens1`, rounded rectangle, ≈ 50 × 31 mm (00:45–00:50);
  - `lens2`, rounder, ≈ 52 × 38 mm (00:51–00:54).
- **Sheets:** all three Letter prints from `training/make_charuco_sheet.py`: ChArUco with a blank window,
  ChArUco with a Ronchi window, and the Ronchi-only sheet (no markers).
- **Conditions:** lit from below (laptop screen) or not, room light or dim, straight and steep angles,
  zoom, portrait and landscape; some frames also show other sheets or the other lens.

| | lens1 | lens2 |
|---|---|---|
| `charuco-blank` | 23 | 24 |
| `charuco-ronchi` | 18 | 18 |
| `ronchi` (no markers) | 17 | 19 |

Sheet labels come from stripe detection in the rectified window (or the image centre when no board is
found), with 26 labels set by eye where that failed (`sheet_source` = `eye`). The lens comes from the v5
measurement when there is one (`lens_source` = `measured`), otherwise from the time: lens 1 was used until
00:50, lens 2 from 00:51. The ≈ sizes above are repeatability results from the v5 prototype, not caliper
values.
