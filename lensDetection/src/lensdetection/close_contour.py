"""Close the open lens contour left by glass-edges with a cubic Bezier spline."""

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

from lensdetection.glass_edges import read_image


def load_results(directory: Path) -> tuple[np.ndarray, dict, np.ndarray | None]:
    edges = cv2.imread(str(directory / "edges.png"), cv2.IMREAD_GRAYSCALE)
    if edges is None:
        raise ValueError(f"Cannot read {directory / 'edges.png'}")
    try:
        detections = json.loads((directory / "detections.json").read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid detections.json: {error}") from error
    circle = detections.get("hough_circle") if isinstance(detections, dict) else None
    if not isinstance(circle, dict) or "ellipse" not in circle:
        raise ValueError(
            "detections.json has no fitted ellipse; run glass-edges on a photo where "
            "the lens rim is found first."
        )
    detail = cv2.imread(str(directory / "highpass.png"), cv2.IMREAD_GRAYSCALE)
    return edges, detections, detail


def unit_frame(ellipse: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the ellipse centre, rotation, and semi-axes (image <-> unit circle)."""
    center = np.asarray(ellipse["center_px"], dtype=np.float64)
    axes = np.asarray(ellipse["axes_px"], dtype=np.float64) / 2
    angle = math.radians(ellipse["angle_degrees"])
    rotation = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    if not (np.isfinite(center).all() and np.isfinite(axes).all() and (axes > 0).all()):
        raise ValueError("The fitted ellipse is not valid.")
    return center, rotation, axes


def rim_knots(
    edges: np.ndarray, ellipse: dict, count: int = 48, min_pixels: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """One knot per angular span around the lens, in image coordinates.

    Edge pixels are mapped into the ellipse's unit-circle frame, so a span's
    radius is relative to the fitted ellipse and works for any aspect ratio.
    A span with too few edge pixels is a gap: its radius is interpolated
    across the gap, which leaves a smooth ellipse-like bridge.
    Returns the knots and a boolean array marking the measured ones.
    """
    center, rotation, axes = unit_frame(ellipse)
    ys, xs = np.nonzero(edges)
    local = (np.stack([xs, ys], axis=1) - center) @ rotation
    unit = local / axes
    angle = np.arctan2(unit[:, 1], unit[:, 0])
    rho = np.hypot(unit[:, 0], unit[:, 1])
    span = ((angle + np.pi) / (2 * np.pi) * count).astype(int) % count
    radius = np.full(count, np.nan)
    for i in range(count):
        in_span = rho[span == i]
        if in_span.size >= min_pixels:
            radius[i] = np.median(in_span)
    measured = ~np.isnan(radius)
    if measured.sum() < 3:
        raise ValueError("Too few rim edges to build a contour.")
    indices = np.arange(count)
    radius = np.interp(indices, indices[measured], radius[measured], period=count)
    theta = (indices + 0.5) / count * 2 * np.pi - np.pi
    unit_knots = np.stack([radius * np.cos(theta), radius * np.sin(theta)], axis=1)
    knots = (unit_knots * axes) @ rotation.T + center
    return knots, measured


def closed_bezier(knots: np.ndarray) -> np.ndarray:
    """Cubic Bezier segments, shape (n, 4, 2), through the knots (Catmull-Rom)."""
    following = np.roll(knots, -1, axis=0)
    preceding = np.roll(knots, 1, axis=0)
    tangent = (following - preceding) / 2
    segments = np.empty((len(knots), 4, 2))
    segments[:, 0] = knots
    segments[:, 1] = knots + tangent / 3
    segments[:, 2] = following - np.roll(tangent, -1, axis=0) / 3
    segments[:, 3] = following
    return segments


def sample_bezier(segments: np.ndarray, per_segment: int = 16) -> np.ndarray:
    t = np.linspace(0, 1, per_segment, endpoint=False)[:, None]
    points = []
    for p0, p1, p2, p3 in segments:
        points.append(
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t**2 * p2
            + t**3 * p3
        )
    return np.concatenate(points)


def svg_path(segments: np.ndarray) -> str:
    parts = [f"M {segments[0, 0, 0]:.2f} {segments[0, 0, 1]:.2f}"]
    for _, p1, p2, p3 in segments:
        parts.append(
            f"C {p1[0]:.2f} {p1[1]:.2f} {p2[0]:.2f} {p2[1]:.2f} {p3[0]:.2f} {p3[1]:.2f}"
        )
    return " ".join(parts) + " Z"


def draw_contour(
    background: np.ndarray,
    edges: np.ndarray,
    curve: np.ndarray,
    segments: int,
    bridged: np.ndarray,
) -> np.ndarray:
    """Draw the input edges and the spline (green measured, blue bridged)."""
    overlay = background.copy()
    overlay[edges > 0] = (0, 0, 255)
    per_segment = len(curve) // segments
    for i, is_bridged in enumerate(bridged):
        piece = np.round(curve[i * per_segment : (i + 1) * per_segment + 1])
        if i == segments - 1:
            piece = np.vstack([piece, np.round(curve[:1])])
        color = (255, 128, 0) if is_bridged else (0, 255, 0)
        cv2.polylines(overlay, [piece.astype(np.int32)], False, color, 2)
    return overlay


def close_contour(
    edges: np.ndarray,
    detections: dict,
    image: np.ndarray | None = None,
    knots: int = 48,
    min_coverage: float = 0.5,
    detail: np.ndarray | None = None,
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray, str]:
    """Return a result dict, filled mask, overlay, high-pass overlay, and SVG.

    The overlay is drawn on the photo (or the edges when there is none); the
    high-pass overlay is drawn on the high-pass image (or the edges).
    """
    if knots < 8:
        raise ValueError("At least 8 knots are needed.")
    if not 0 <= min_coverage <= 1:
        raise ValueError("Minimum coverage must be between 0 and 1.")
    if image is not None and image.shape[:2] != edges.shape:
        raise ValueError("The image and edges.png must have identical dimensions.")
    if detail is not None and detail.shape != edges.shape:
        raise ValueError("highpass.png and edges.png must have identical dimensions.")
    points, measured = rim_knots(edges, detections["hough_circle"]["ellipse"], knots)
    coverage = float(measured.mean())
    segments = closed_bezier(points)
    curve = sample_bezier(segments)
    homography = np.asarray(detections["board_to_image_homography"], dtype=np.float64)
    physical = cv2.perspectiveTransform(
        curve.astype(np.float32).reshape(-1, 1, 2), np.linalg.inv(homography)
    ).reshape(-1, 2)
    area_mm2 = abs(cv2.contourArea(physical.astype(np.float32)))
    polygon = np.round(curve).astype(np.int32).reshape(-1, 1, 2)
    mask = np.zeros(edges.shape, np.uint8)
    cv2.fillPoly(mask, [polygon], 255)

    # A segment is bridged when either end span had no edge pixels.
    bridged = ~(measured & np.roll(measured, -1))
    plain = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    overlay = draw_contour(
        plain if image is None else image, edges, curve, len(segments), bridged
    )
    detail_overlay = draw_contour(
        plain if detail is None else cv2.cvtColor(detail, cv2.COLOR_GRAY2BGR),
        edges,
        curve,
        len(segments),
        bridged,
    )

    result = {
        "status": "closed" if coverage >= min_coverage else "too_open",
        "knots": knots,
        "measured_fraction": coverage,
        "bridged_segments": [int(i) for i in np.flatnonzero(bridged)],
        "area_mm2": area_mm2,
        "perimeter_mm": float(
            cv2.arcLength(physical.astype(np.float32).reshape(-1, 1, 2), True)
        ),
        "bezier_px": segments.tolist(),
        "contour_board_mm": physical.tolist(),
    }
    height, width = edges.shape
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        f'<path d="{svg_path(segments)}" fill="none" stroke="black" stroke-width="2"/>'
        "</svg>\n"
    )
    return result, mask, overlay, detail_overlay, svg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results", type=Path, help="glass-edges output folder (edges.png, detections.json)"
    )
    parser.add_argument("--image", type=Path, help="Photo to draw the overlay on")
    parser.add_argument(
        "--output-dir", type=Path, help="Where to write results (default: the results folder)"
    )
    parser.add_argument(
        "--knots",
        type=int,
        default=48,
        help="Spline knots around the lens (default: 48)",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.5,
        help="Smallest fraction of the rim that must be measured (default: 0.5)",
    )
    args = parser.parse_args()
    output_dir = args.output_dir or args.results
    try:
        edges, detections, detail = load_results(args.results)
        image = read_image(args.image) if args.image is not None else None
        result, mask, overlay, detail_overlay, svg = close_contour(
            edges, detections, image, args.knots, args.min_coverage, detail
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, picture in (
            ("closed_mask.png", mask),
            ("closed_overlay.png", overlay),
            ("closed_highpass_overlay.png", detail_overlay),
        ):
            if not cv2.imwrite(str(output_dir / name), picture):
                raise OSError(f"Could not write image: {output_dir / name}")
        (output_dir / "closed.svg").write_text(svg)
        (output_dir / "closed.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n"
        )
    except (OSError, ValueError, KeyError, cv2.error) as error:
        parser.exit(2, f"close-contour: {error}\n")
    print(
        f"{result['measured_fraction']:.0%} of the rim measured, "
        f"{len(result['bridged_segments'])} bridged segment(s); "
        f"results in {output_dir}"
    )
    if result["status"] != "closed":
        parser.exit(1, "Too little of the rim was measured to trust the closure.\n")


if __name__ == "__main__":
    main()
