"""Detect candidate glass outlines over a measured rectangular Ronchi ruling."""

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path

import cv2
import numpy as np

from lensdetection.glass_edges import read_image


@dataclass(frozen=True)
class RonchiPattern:
    width_mm: float
    height_mm: float
    bar_width_mm: float
    corners_px: np.ndarray


def load_pattern(path: Path) -> RonchiPattern:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Pattern JSON must be an object.")
    required = ("width_mm", "height_mm", "bar_width_mm", "corners_px")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing pattern fields: {', '.join(missing)}")
    for key in required[:3]:
        value = data[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be a finite positive number.")
    if data["width_mm"] / data["bar_width_mm"] < 8:
        raise ValueError("The measured region must span at least eight bars.")
    points = data["corners_px"]
    if (
        not isinstance(points, list) or len(points) != 4
        or any(
            not isinstance(point, list) or len(point) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in point)
            for point in points
        )
    ):
        raise ValueError("corners_px must contain four finite [x, y] pairs.")
    corners = np.array(points, dtype=np.float32)
    if not np.isfinite(corners).all():
        raise ValueError("Corner coordinates exceed OpenCV's coordinate range.")
    if not cv2.isContourConvex(corners) or cv2.contourArea(corners, oriented=True) <= 0:
        raise ValueError("corners_px must form a convex clockwise quadrilateral.")
    return RonchiPattern(
        data["width_mm"], data["height_mm"], data["bar_width_mm"], corners
    )


def rectify(
    image: np.ndarray, pattern: RonchiPattern
) -> tuple[np.ndarray, np.ndarray, float]:
    height, width = image.shape[:2]
    corners = pattern.corners_px
    if (
        (corners[:, 0] < 0).any() or (corners[:, 0] > width - 1).any()
        or (corners[:, 1] < 0).any() or (corners[:, 1] > height - 1).any()
    ):
        raise ValueError("All pattern corners must be inside the image.")
    lengths = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
    scale = float(min(
        min(lengths[0], lengths[2]) / pattern.width_mm,
        min(lengths[1], lengths[3]) / pattern.height_mm,
    ))
    if not math.isfinite(scale) or scale * pattern.bar_width_mm < 6:
        raise ValueError("Each bar must span at least six pixels; use a closer photo.")
    out_width = round(pattern.width_mm * scale) + 1
    out_height = round(pattern.height_mm * scale) + 1
    if out_width < 16 or out_height < 16 or out_width * out_height > 20_000_000:
        raise ValueError("Rectified pattern dimensions are too small or too large.")
    destination = np.array([
        [0, 0], [pattern.width_mm * scale, 0],
        [pattern.width_mm * scale, pattern.height_mm * scale],
        [0, pattern.height_mm * scale],
    ], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(corners, destination)
    if not np.isfinite(transform).all() or np.linalg.cond(transform) > 1e12:
        raise ValueError("Pattern perspective transform is degenerate.")
    rectified = cv2.warpPerspective(image, transform, (out_width, out_height))
    return rectified, transform, scale


def detect_ronchi_glass(
    image: np.ndarray,
    pattern: RonchiPattern,
    threshold: float = 30.0,
    min_area_mm2: float = 1.0,
    reference: np.ndarray | None = None,
) -> tuple[dict, dict[str, np.ndarray]]:
    if not math.isfinite(threshold) or not 0 < threshold < 255:
        raise ValueError("Threshold must be between 0 and 255.")
    if not math.isfinite(min_area_mm2) or min_area_mm2 <= 0:
        raise ValueError("Minimum area must be finite and positive.")
    rectified, transform, scale = rectify(image, pattern)
    gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
    observed = cv2.GaussianBlur(gray, (5, 5), 1.0).astype(np.float32)
    if reference is not None:
        if reference.shape != image.shape:
            raise ValueError("Reference and glass images must have identical dimensions.")
        aligned = cv2.warpPerspective(
            reference, transform, (gray.shape[1], gray.shape[0])
        )
        source = cv2.GaussianBlur(
            cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY), (5, 5), 1.0
        ).astype(np.float32)
    else:
        source = observed
    # A vertical ruling repeats along rows. The median rejects localized glass
    # effects, provided most rows in each column still show the bare pattern.
    profile = np.median(source, axis=0)
    black, white = np.percentile(profile, [10, 90])
    if white - black < 40:
        raise ValueError("Ronchi pattern contrast is too low.")
    transitions = np.flatnonzero(np.diff(profile > (black + white) / 2)) + 1
    if len(transitions) < 6:
        raise ValueError("Cannot identify enough Ronchi bars in the selected region.")
    bar_px = pattern.bar_width_mm * scale
    widths = np.diff(transitions)
    if np.mean(np.abs(widths - bar_px) <= max(2, bar_px * 0.2)) < 0.8:
        raise ValueError(
            "Observed bars do not match bar_width_mm. Check corners, dimensions, "
            "and orientation: bars must run from the top to the bottom edge."
        )
    if reference is None:
        background = np.broadcast_to(profile, observed.shape)
    else:
        background = source
        # Only global exposure changes are compensated; the reference camera
        # and ruling must not move because parallel bars cannot register both axes.
        obs_black, obs_white = np.percentile(observed, [10, 90])
        if obs_white - obs_black < 40:
            raise ValueError("Glass image contrast is too low.")
        background = (background - black) * ((obs_white - obs_black) / (white - black)) + obs_black
    residual = np.abs(observed - background)
    stripe_edges = np.zeros(gray.shape, np.uint8)
    stripe_edges[:, transitions] = 255
    stripe_edges = cv2.dilate(stripe_edges, np.ones((3, 3), np.uint8))
    evidence = ((residual >= threshold) & (stripe_edges == 0)).astype(np.uint8) * 255
    # A displaced stripe leaves periodic residual bands: bridge one bar across
    # the ruling, with less gap filling along the bars to preserve the outline.
    across = max(5, round(bar_px * 1.1) | 1)
    along = max(5, round(bar_px * 0.4) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (across, along))
    connected = cv2.morphologyEx(evidence, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    inverse = np.linalg.inv(transform)
    overlay = image.copy()
    rectified_mask = np.zeros(gray.shape, np.uint8)
    candidates = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour) / scale**2
        if len(contour) < 3 or area < min_area_mm2:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if x <= 1 or y <= 1 or x + w >= gray.shape[1] - 1 or y + h >= gray.shape[0] - 1:
            continue
        contour_mm = contour.astype(np.float32) / scale
        contour_px = cv2.perspectiveTransform(contour.astype(np.float32), inverse)
        display_contour = np.rint(contour_px).astype(np.int32)
        number = len(candidates) + 1
        cv2.drawContours(rectified_mask, [contour], -1, 255, cv2.FILLED)
        cv2.drawContours(overlay, [display_contour], -1, (0, 255, 0), 2)
        label_x, label_y = display_contour.reshape(-1, 2).min(axis=0)
        cv2.putText(overlay, str(number), (int(label_x), max(15, int(label_y) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        candidates.append({
            "id": number,
            "contour_px": contour_px.reshape(-1, 2).tolist(),
            "contour_pattern_mm": contour_mm.reshape(-1, 2).tolist(),
            "area_mm2": area,
            "perimeter_mm": float(cv2.arcLength(contour_mm, True)),
        })
    mask = cv2.warpPerspective(
        rectified_mask, inverse, (image.shape[1], image.shape[0]),
        flags=cv2.INTER_NEAREST,
    )
    edges = cv2.subtract(mask, cv2.erode(mask, np.ones((3, 3), np.uint8)))
    result = {
        "status": "candidates_found" if candidates else "no_candidates",
        "image_size_px": [image.shape[1], image.shape[0]],
        "pattern_to_image_homography": (
            inverse @ np.diag([scale, scale, 1.0])
        ).tolist(),
        "rectified_pixels_per_mm": scale,
        "measured_bar_width_px": float(np.median(widths)),
        "background_source": "reference" if reference is not None else "column_median",
        "residual_threshold": threshold,
        "min_area_mm2": min_area_mm2,
        "candidates": candidates,
    }
    return result, {
        "overlay.png": overlay, "mask.png": mask, "edges.png": edges,
        "rectified.png": rectified,
        "residual.png": np.clip(residual, 0, 255).astype(np.uint8),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("pattern", type=Path, help="Ronchi dimensions and image corners JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("ronchi-edges"))
    parser.add_argument("--reference", type=Path, help="Bare pattern, same camera and lighting")
    parser.add_argument("--threshold", type=float, default=30.0)
    parser.add_argument("--min-area-mm2", type=float, default=1.0)
    args = parser.parse_args()
    try:
        names = ("detections.json", "overlay.png", "mask.png", "edges.png",
                 "rectified.png", "residual.png")
        inputs = {p.resolve() for p in (args.image, args.pattern, args.reference)
                  if p is not None}
        if any((args.output_dir / name).resolve() in inputs for name in names):
            raise ValueError("Output paths must not overwrite input files.")
        pattern = load_pattern(args.pattern)
        image = read_image(args.image)
        reference = read_image(args.reference) if args.reference is not None else None
        result, images = detect_ronchi_glass(
            image, pattern, args.threshold, args.min_area_mm2, reference
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, output in images.items():
            path = args.output_dir / name
            if not cv2.imwrite(str(path), output):
                raise OSError(f"Could not write image: {path}")
        (args.output_dir / "detections.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n"
        )
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"ronchi-edges: {error}\n")
    print(f"{len(result['candidates'])} candidate(s); results in {args.output_dir}")
    if not result["candidates"]:
        parser.exit(1, "No glass outline found; inspect residual.png or improve lighting.\n")


if __name__ == "__main__":
    main()
