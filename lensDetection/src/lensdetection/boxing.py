"""Measure a lens with the boxing method from glass-edges and close-contour results.

The boxing system encloses the lens in the smallest rectangle whose sides are
parallel and perpendicular to the horizontal datum line. Its width is the
lens's horizontal size (A, "length") and its height the vertical size (B,
"wideness"). The datum is the board's x axis unless --angle tilts it.
"""

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

from lensdetection.glass_edges import read_image

BOX_COLOR = (0, 255, 255)
LENS_COLOR = (0, 255, 0)
DIMENSION_COLOR = (255, 128, 0)


def load_results(directory: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return the closed lens contour in board millimeters and the board-to-image homography."""
    try:
        closed = json.loads((directory / "closed.json").read_text())
        detections = json.loads((directory / "detections.json").read_text())
    except FileNotFoundError as error:
        raise ValueError(f"{error.filename} not found; run glass-edges and close-contour first.") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {directory}: {error}") from error
    contour = np.asarray(closed["contour_board_mm"], dtype=np.float64)
    homography = np.asarray(detections["board_to_image_homography"], dtype=np.float64)
    if contour.ndim != 2 or contour.shape[0] < 3 or contour.shape[1] != 2:
        raise ValueError("closed.json has no valid contour.")
    if homography.shape != (3, 3) or not np.isfinite(homography).all():
        raise ValueError("detections.json has no valid board homography.")
    return contour, homography


def rotation(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    return np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])


def measure_box(contour_mm: np.ndarray, angle_degrees: float = 0.0) -> dict:
    """Box the contour in a frame whose x axis is the datum line.

    Everything is returned in board millimeters. Frame coordinates are the
    board coordinates rotated so the datum becomes horizontal.
    """
    frame = rotation(angle_degrees)
    local = contour_mm @ frame  # board -> datum frame (row-vector form of R^T p)
    low = local.min(axis=0)
    high = local.max(axis=0)
    corners_local = np.array([[low[0], low[1]], [high[0], low[1]], [high[0], high[1]], [low[0], high[1]]])
    center_local = (low + high) / 2
    width, height = (high - low).tolist()
    return {
        "datum_angle_degrees": angle_degrees,
        "length_mm": width,
        "width_mm": height,
        "aspect_ratio": width / height,
        "box_center_board_mm": (center_local @ frame.T).tolist(),
        "box_corners_board_mm": (corners_local @ frame.T).tolist(),
        "frame": frame.tolist(),
        "low_local": low.tolist(),
        "high_local": high.tolist(),
        "contact_points_board_mm": [
            contour_mm[int(np.argmin(local[:, 0]))].tolist(),
            contour_mm[int(np.argmax(local[:, 0]))].tolist(),
            contour_mm[int(np.argmin(local[:, 1]))].tolist(),
            contour_mm[int(np.argmax(local[:, 1]))].tolist(),
        ],
    }


def to_image(points_mm: np.ndarray, homography: np.ndarray) -> np.ndarray:
    points = np.asarray(points_mm, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(points, homography).reshape(-1, 2)


def draw_label(image: np.ndarray, text: str, center: np.ndarray, scale: float, thickness: int) -> None:
    (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x = int(round(center[0] - w / 2))
    y = int(round(center[1] + h / 2))
    cv2.rectangle(image, (x - 4, y - h - 4), (x + w + 4, y + baseline + 2), (0, 0, 0), cv2.FILLED)
    cv2.putText(
        image,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )


def draw_dimension(
    image: np.ndarray,
    start_mm: np.ndarray,
    end_mm: np.ndarray,
    homography: np.ndarray,
    text: str,
    scale: float,
    thickness: int,
) -> None:
    """Double-headed arrow between two board points, with its length printed on it."""
    a, b = to_image(np.array([start_mm, end_mm]), homography)
    cv2.arrowedLine(
        image,
        tuple(np.round(a).astype(int)),
        tuple(np.round(b).astype(int)),
        DIMENSION_COLOR,
        thickness,
        cv2.LINE_AA,
        tipLength=0.04,
    )
    cv2.arrowedLine(
        image,
        tuple(np.round(b).astype(int)),
        tuple(np.round(a).astype(int)),
        DIMENSION_COLOR,
        thickness,
        cv2.LINE_AA,
        tipLength=0.04,
    )
    draw_label(image, text, (a + b) / 2, scale, max(1, thickness // 2))


def draw_overlay(image: np.ndarray, contour_mm: np.ndarray, homography: np.ndarray, box: dict) -> np.ndarray:
    """Draw the lens, its boxing rectangle, the contact points, and dimension lines."""
    overlay = image.copy()
    scale = max(image.shape[:2]) / 1600
    thickness = max(2, round(3 * scale))
    font = max(0.6, 0.9 * scale)
    frame = np.asarray(box["frame"])
    low = np.asarray(box["low_local"])
    high = np.asarray(box["high_local"])
    span = high - low
    margin = 0.12 * float(span.min())

    def board(x: float, y: float) -> np.ndarray:
        return np.array([x, y]) @ frame.T

    cv2.polylines(
        overlay,
        [np.round(to_image(contour_mm, homography)).astype(np.int32)],
        True,
        LENS_COLOR,
        thickness,
        cv2.LINE_AA,
    )
    quad = np.round(to_image(np.array(box["box_corners_board_mm"]), homography))
    cv2.polylines(overlay, [quad.astype(np.int32)], True, BOX_COLOR, thickness, cv2.LINE_AA)
    for point in to_image(np.array(box["contact_points_board_mm"]), homography):
        cv2.circle(overlay, tuple(np.round(point).astype(int)), thickness * 2, (0, 0, 255), -1)

    # The datum line and box centre mark the frame of reference.
    middle = (low + high) / 2
    cross = margin / 2
    for a, b in (
        (board(middle[0] - cross, middle[1]), board(middle[0] + cross, middle[1])),
        (board(middle[0], middle[1] - cross), board(middle[0], middle[1] + cross)),
    ):
        p, q = to_image(np.array([a, b]), homography)
        cv2.line(
            overlay,
            tuple(np.round(p).astype(int)),
            tuple(np.round(q).astype(int)),
            BOX_COLOR,
            thickness,
            cv2.LINE_AA,
        )

    draw_dimension(
        overlay,
        board(low[0], low[1] - margin),
        board(high[0], low[1] - margin),
        homography,
        f"A = {box['length_mm']:.2f} mm",
        font,
        thickness,
    )
    draw_dimension(
        overlay,
        board(high[0] + margin, low[1]),
        board(high[0] + margin, high[1]),
        homography,
        f"B = {box['width_mm']:.2f} mm",
        font,
        thickness,
    )
    lines = [
        f"Length (A): {box['length_mm']:.2f} mm",
        f"Width  (B): {box['width_mm']:.2f} mm",
        f"A/B: {box['aspect_ratio']:.3f}",
    ]
    if box["datum_angle_degrees"]:
        lines.append(f"Datum: {box['datum_angle_degrees']:.1f} deg")
    for i, line in enumerate(lines):
        cv2.putText(
            overlay,
            line,
            (int(20 * scale) + 10, int((40 + 40 * i) * scale) + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            font,
            (0, 0, 0),
            thickness + 3,
            cv2.LINE_AA,
        )
        cv2.putText(
            overlay,
            line,
            (int(20 * scale) + 10, int((40 + 40 * i) * scale) + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            font,
            (255, 255, 255),
            thickness - 1,
            cv2.LINE_AA,
        )
    return overlay


def measure(
    image: np.ndarray,
    contour_mm: np.ndarray,
    homography: np.ndarray,
    angle: float = 0.0,
) -> tuple[dict, np.ndarray]:
    box = measure_box(contour_mm, angle)
    overlay = draw_overlay(image, contour_mm, homography, box)
    public = {k: v for k, v in box.items() if k not in ("frame", "low_local", "high_local")}
    return public, overlay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results",
        type=Path,
        help="glass-edges output folder that close-contour also ran in (closed.json, detections.json)",
    )
    parser.add_argument("image", type=Path, help="Photo to draw the overlay on")
    parser.add_argument(
        "--angle",
        type=float,
        default=0.0,
        help="Datum line angle in degrees from the board's x axis, counter-clockwise on the board (default: 0)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Where to write results (default: the results folder)",
    )
    args = parser.parse_args()
    output_dir = args.output_dir or args.results
    try:
        image = read_image(args.image)
        contour, homography = load_results(args.results)
        result, overlay = measure(image, contour, homography, args.angle)
        output_dir.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_dir / "boxing_overlay.png"), overlay):
            raise OSError(f"Could not write image: {output_dir / 'boxing_overlay.png'}")
        (output_dir / "boxing.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, KeyError, cv2.error) as error:
        parser.exit(2, f"boxing: {error}\n")
    print(f"Length (A) {result['length_mm']:.2f} mm, width (B) {result['width_mm']:.2f} mm; results in {output_dir}")


if __name__ == "__main__":
    main()
