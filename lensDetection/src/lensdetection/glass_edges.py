"""Find a round glass outline over a ChArUco board: high-pass, Hough circle, Canny."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from lensdetection.aruco import DICTIONARIES


def load_board(path: Path) -> cv2.aruco.CharucoBoard:
    """Read physical board dimensions matching the charuco generator."""
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Board JSON must be an object.")
    required = ("squares_x", "squares_y", "square_mm", "marker_mm", "dictionary")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing board fields: {', '.join(missing)}")
    for key in ("squares_x", "squares_y"):
        if type(data[key]) is not int or data[key] < 3:
            raise ValueError(f"{key} must be an integer of at least 3.")
    for key in ("square_mm", "marker_mm"):
        if type(data[key]) not in (int, float) or not math.isfinite(data[key]) or data[key] <= 0:
            raise ValueError(f"{key} must be a finite positive number.")
    if data["marker_mm"] >= data["square_mm"]:
        raise ValueError("marker_mm must be smaller than square_mm.")
    name = data["dictionary"]
    if not isinstance(name, str) or name not in DICTIONARIES:
        raise ValueError(f"dictionary must be one of: {', '.join(sorted(DICTIONARIES))}")
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARIES[name])
    if data["squares_x"] * data["squares_y"] // 2 > len(dictionary.bytesList):
        raise ValueError("The dictionary does not contain enough marker IDs.")
    if not all(math.isfinite(data[key] * data["square_mm"]) for key in ("squares_x", "squares_y")):
        raise ValueError("Board dimensions are too large.")
    board = cv2.aruco.CharucoBoard(
        (data["squares_x"], data["squares_y"]),
        data["square_mm"],
        data["marker_mm"],
        dictionary,
    )
    if not np.isfinite(board.getChessboardCorners()).all():
        raise ValueError("Board dimensions exceed OpenCV's coordinate range.")
    return board


def locate_board(gray: np.ndarray, board: cv2.aruco.CharucoBoard) -> tuple:
    corners, ids, _, _ = cv2.aruco.CharucoDetector(board).detectBoard(gray)
    if ids is None or len(ids) < 6:
        raise ValueError(
            "At least six visible ChArUco corners are needed. Keep uncovered "
            "markers around the glass and use the board's exact JSON settings."
        )
    board_corners = np.asarray(board.getChessboardCorners(), dtype=np.float32)
    ids_idx = np.asarray(ids, dtype=np.intp).ravel()
    physical = board_corners[ids_idx, :2]
    if np.linalg.matrix_rank(physical - physical.mean(axis=0)) < 2:
        raise ValueError("Visible board corners must span both board directions.")
    homography, inliers = cv2.findHomography(physical, corners.reshape(-1, 2), cv2.RANSAC, 2.0)
    if homography is None or inliers is None or int(inliers.sum()) < 6:
        raise ValueError("Could not reliably fit the board plane to the image.")
    selected = inliers.ravel().astype(bool)
    if np.linalg.matrix_rank(physical[selected] - physical[selected].mean(axis=0)) < 2:
        raise ValueError("Inlier corners do not span the board plane.")
    if not np.isfinite(homography).all() or np.linalg.cond(homography) > 1e12:
        raise ValueError("Board homography is degenerate.")
    projected = cv2.perspectiveTransform(physical[selected, None], homography)
    errors = np.linalg.norm(projected.reshape(-1, 2) - corners.reshape(-1, 2)[selected], axis=1)
    return homography, int(selected.sum()), float(np.sqrt(np.mean(errors**2)))


def render_background(
    shape: tuple[int, int], board: cv2.aruco.CharucoBoard, homography: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float]:
    sx, sy = board.getChessboardSize()
    square = board.getSquareLength()
    # Render at camera resolution (with a cap), rather than a fixed physical scale.
    physical = np.array(
        [[0, 0], [sx * square, 0], [sx * square, sy * square], [0, sy * square]],
        dtype=np.float32,
    )
    outline = cv2.perspectiveTransform(physical[:, None], homography)
    if not np.isfinite(outline).all():
        raise ValueError("Board projection is not finite.")
    area = abs(cv2.contourArea(outline))
    pixels_per_square = math.sqrt(area / (sx * sy))
    if pixels_per_square < 12:
        raise ValueError("Board squares are too small in the image; use a closer photo.")
    tile = max(32, min(256, round(pixels_per_square * 2)))
    template = board.generateImage((sx * tile, sy * tile), marginSize=0, borderBits=1)
    template_to_mm = np.diag([square / tile, square / tile, 1.0])
    transform = homography @ template_to_mm
    height, width = shape
    expected = cv2.warpPerspective(template, transform, (width, height), borderValue=255)
    footprint = cv2.warpPerspective(
        np.full(template.shape, 255, np.uint8),
        transform,
        (width, height),
        flags=cv2.INTER_NEAREST,
    )
    # Never interpret the board border or the surrounding scene as glass.
    margin = max(3, round(pixels_per_square * 0.06))
    footprint = cv2.erode(
        footprint,
        np.ones((2 * margin + 1, 2 * margin + 1), np.uint8),
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    if cv2.countNonZero(footprint) < 100:
        raise ValueError("Too little of the board is visible in the image.")
    return expected, footprint, pixels_per_square


def high_pass(gray: np.ndarray, pixels_per_square: float, gain: float = 2.0) -> np.ndarray:
    """Subtract a heavy blur and amplify, so faint thin details such as a glass
    rim stand out against the board's broad black and white areas."""
    sigma = float(np.clip(pixels_per_square * 0.1, 2.0, 25.0))
    background = cv2.GaussianBlur(gray, (0, 0), sigma).astype(np.float32)
    detail = (gray.astype(np.float32) - background) * gain + 128
    return np.clip(detail, 0, 255).astype(np.uint8)


def board_axis_angles(homography: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Image directions (radians, shape (n, 2)) of the board's x and y axes at pixels."""
    q = np.linalg.inv(homography) @ np.stack([xs, ys, np.ones(len(xs))])
    q = q / q[2]
    p = homography @ q
    w = p[2]
    angles = []
    for column in (0, 1):
        h = homography[:, column]
        dx = (h[0] - p[0] / w * h[2]) / w
        dy = (h[1] - p[1] / w * h[2]) / w
        angles.append(np.arctan2(dy, dx))
    return np.stack(angles, axis=1)


def rim_candidate_edges(
    detail: np.ndarray,
    expected: np.ndarray,
    footprint: np.ndarray,
    pixels_per_square: float,
    homography: np.ndarray,
    max_angle_degrees: float = 20.0,
) -> np.ndarray:
    """Canny edges of the high-pass image, minus the board's own printed edges.

    The rendered board's edges are dilated into a band wide enough to absorb
    registration and lens-distortion drift. Inside the band, an edge pixel is
    printed pattern only if it also runs along one of the board's two axes;
    a rim crossing a printed edge at an angle keeps its pixels there.
    """
    blurred = cv2.GaussianBlur(detail, (0, 0), 2.0)
    edges = cv2.Canny(blurred, 40, 120)
    radius = max(2, round(pixels_per_square * 0.04))
    band = cv2.dilate(cv2.Canny(expected, 50, 150), np.ones((2 * radius + 1,) * 2, np.uint8))
    ys, xs = np.nonzero((edges > 0) & (band > 0))
    if xs.size:
        smooth = blurred.astype(np.float32)
        gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)[ys, xs]
        gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)[ys, xs]
        tangent = np.arctan2(gy, gx) + np.pi / 2
        axes = board_axis_angles(homography, xs.astype(np.float64), ys.astype(np.float64))
        # Angle between lines, folded into [0, 90] degrees.
        difference = np.abs((tangent[:, None] - axes + np.pi / 2) % np.pi - np.pi / 2)
        printed = (difference < math.radians(max_angle_degrees)).any(axis=1)
        edges[ys[printed], xs[printed]] = 0
    edges[footprint == 0] = 0
    # Drop specks and short slivers that cannot be part of a rim.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    for label in range(1, count):
        if max(stats[label, cv2.CC_STAT_WIDTH], stats[label, cv2.CC_STAT_HEIGHT]) < (pixels_per_square * 0.1):
            edges[labels == label] = 0
    return edges


def ring_coverage(ys: np.ndarray, xs: np.ndarray, circle: tuple, tolerance: float, bins: int) -> float:
    """Fraction of angular bins around a circle that hold an edge pixel."""
    cx, cy, radius = circle
    dx, dy = xs - cx, ys - cy
    near = np.abs(np.hypot(dx, dy) - radius) <= tolerance * radius
    if not near.any():
        return 0.0
    angle = np.arctan2(dy[near], dx[near])
    index = ((angle + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    return float(np.unique(index).size) / bins


def find_round_edge(
    edges: np.ndarray,
    min_radius: float,
    max_radius: float,
    tolerance: float,
    bins: int = 72,
    min_coverage: float = 0.6,
    max_circles: int = 30,
) -> tuple[tuple[float, float, float], float] | None:
    """Hough circle transform over the rim-candidate edges.

    Returns the circle (cx, cy, radius) whose ring is supported by edge pixels
    all the way around, together with that coverage, or None.
    """
    ys, xs = np.nonzero(edges)
    if xs.size == 0:
        return None
    scale = min(1.0, 1000 / max(edges.shape))
    small = cv2.resize(edges, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = cv2.normalize(cv2.GaussianBlur(small, (0, 0), 3), None, 0, 255, cv2.NORM_MINMAX)
    circles = cv2.HoughCircles(
        small,
        cv2.HOUGH_GRADIENT,
        dp=2,
        minDist=max(4.0, min_radius * scale * 0.5),
        param1=60,
        param2=10,
        minRadius=max(1, int(min_radius * scale)),
        maxRadius=max(2, math.ceil(max_radius * scale)),
    )
    if circles is None:
        return None
    best = None
    for cx, cy, radius in circles[0][:max_circles] / scale:
        circle = (float(cx), float(cy), float(radius))
        coverage = ring_coverage(ys, xs, circle, tolerance, bins)
        if best is None or coverage > best[1]:
            best = (circle, coverage)
    if best is None or best[1] < min_coverage:
        return None
    return best


def ellipse_offsets(ys: np.ndarray, xs: np.ndarray, ellipse: tuple) -> np.ndarray:
    """Distance of points from an ellipse, relative to its size (0 = on it)."""
    (cx, cy), (width, height), degrees = ellipse
    angle = math.radians(degrees)
    dx, dy = xs - cx, ys - cy
    u = (dx * math.cos(angle) + dy * math.sin(angle)) / (width / 2)
    v = (-dx * math.sin(angle) + dy * math.cos(angle)) / (height / 2)
    return np.abs(np.hypot(u, v) - 1.0)


def isolate_round_edge(
    edges: np.ndarray, circle: tuple, tolerance: float, final_tolerance: float = 0.1
) -> tuple[np.ndarray, tuple | None]:
    """Fit an ellipse to the edges on the Hough circle's ring and keep only its edges.

    Starting from the circle, the ring is narrowed over a few passes so that
    stray edges stop pulling the fit. Returns the isolated edge image and the
    final ellipse ((cx, cy), (width, height), degrees), or None.
    """
    cx, cy, radius = circle
    ys, xs = np.nonzero(edges)
    ellipse = ((cx, cy), (2 * radius, 2 * radius), 0.0)
    keep = None
    for step in (tolerance, (tolerance + final_tolerance) / 2, final_tolerance):
        keep = ellipse_offsets(ys, xs, ellipse) <= step
        if keep.sum() < 20:
            return np.zeros_like(edges), None
        points = np.stack([xs[keep], ys[keep]], axis=1).astype(np.float32)
        points = np.ascontiguousarray(points[:: len(points) // 5000 + 1])
        ellipse = cv2.fitEllipse(points)
    if not all(math.isfinite(v) for v in (*ellipse[0], *ellipse[1])) or min(ellipse[1]) <= 0:
        return np.zeros_like(edges), None
    keep = ellipse_offsets(ys, xs, ellipse) <= final_tolerance
    isolated = np.zeros_like(edges)
    isolated[ys[keep], xs[keep]] = 255
    return isolated, ellipse


def detect_glass(
    image: np.ndarray,
    board: cv2.aruco.CharucoBoard,
    min_area_mm2: float | None = None,
    min_radius_mm: float | None = None,
    max_radius_mm: float | None = None,
    tolerance: float = 0.3,
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return candidates, a filled mask, overlay, high-pass image, and rim edges.

    Steps: locate the board; high-pass filter to bring out details; Hough circle
    transform to find the round edge over the board; Canny edges isolated to
    that edge and fitted with an ellipse, with the board's own printed edges
    removed.
    """
    if min_area_mm2 is not None and (not math.isfinite(min_area_mm2) or min_area_mm2 <= 0):
        raise ValueError("Minimum area must be finite and positive.")
    for name, value in (("Minimum radius", min_radius_mm), ("Maximum radius", max_radius_mm)):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError(f"{name} must be finite and positive.")
    if not math.isfinite(tolerance) or not 0 < tolerance < 1:
        raise ValueError("Ring tolerance must be between 0 and 1.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    homography, inlier_count, reprojection_rms = locate_board(gray, board)
    expected, footprint, pixels_per_square = render_background(gray.shape, board, homography)
    square = board.getSquareLength()
    sx, sy = board.getChessboardSize()
    pixels_per_mm = pixels_per_square / square
    min_radius_mm = square * 0.4 if min_radius_mm is None else min_radius_mm
    max_radius_mm = min(sx, sy) * square / 2 if max_radius_mm is None else max_radius_mm
    if min_radius_mm >= max_radius_mm:
        raise ValueError("Minimum radius must be smaller than maximum radius.")

    detail = high_pass(gray, pixels_per_square)
    candidate_edges = rim_candidate_edges(detail, expected, footprint, pixels_per_square, homography)
    found = find_round_edge(
        candidate_edges,
        min_radius_mm * pixels_per_mm,
        max_radius_mm * pixels_per_mm,
        tolerance,
    )
    mask = np.zeros(gray.shape, np.uint8)
    overlay = image.copy()
    edges = np.zeros(gray.shape, np.uint8)
    candidates = []
    circle_info = None
    if found is not None:
        circle, coverage = found
        edges, ellipse = isolate_round_edge(candidate_edges, circle, tolerance)
        circle_info = {
            "center_px": [circle[0], circle[1]],
            "radius_px": circle[2],
            "edge_coverage": coverage,
        }
        points = np.empty((0, 2), np.float32)
        if ellipse is not None:
            (ex, ey), (ew, eh), degrees = ellipse
            circle_info["ellipse"] = {
                "center_px": [ex, ey],
                "axes_px": [ew, eh],
                "angle_degrees": degrees,
            }
            polygon = cv2.ellipse2Poly(
                (round(ex), round(ey)), (round(ew / 2), round(eh / 2)), round(degrees), 0, 360, 2
            )
            points = polygon.astype(np.float32)
        cv2.circle(
            overlay,
            (round(circle[0]), round(circle[1])),
            round(circle[2]),
            (0, 200, 255),
            2,
        )
        overlay[edges > 0] = (0, 0, 255)
        if len(points) >= 3:
            contour = np.round(points).astype(np.int32).reshape(-1, 1, 2)
            inverse = np.linalg.inv(homography)
            physical = cv2.perspectiveTransform(points.reshape(-1, 1, 2), inverse)
            area_mm2 = abs(cv2.contourArea(physical))
            minimum = square**2 if min_area_mm2 is None else min_area_mm2
            h, w = gray.shape
            xi = np.clip(contour[:, 0, 0], 0, w - 1)
            yi = np.clip(contour[:, 0, 1], 0, h - 1)
            clipped = bool(np.any(footprint[yi, xi] == 0))
            if math.isfinite(area_mm2) and area_mm2 >= minimum and not clipped:
                cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
                cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 2)
                x, y, width, height = cv2.boundingRect(contour)
                cv2.putText(overlay, "1", (x, max(15, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                candidates.append(
                    {
                        "id": 1,
                        "contour_px": contour.reshape(-1, 2).tolist(),
                        "contour_board_mm": physical.reshape(-1, 2).tolist(),
                        "area_mm2": area_mm2,
                        "perimeter_mm": float(cv2.arcLength(physical, True)),
                        "bounding_box_px": [x, y, width, height],
                    }
                )
    result = {
        "status": "candidates_found" if candidates else "no_candidates",
        "image_size_px": [gray.shape[1], gray.shape[0]],
        "board_to_image_homography": homography.tolist(),
        "board_inlier_corners": inlier_count,
        "board_reprojection_rms_px": reprojection_rms,
        "min_area_mm2": square**2 if min_area_mm2 is None else min_area_mm2,
        "hough_circle": circle_info,
        "candidates": candidates,
    }
    return result, mask, overlay, detail, edges


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Photo of glass over a ChArUco board")
    parser.add_argument("board", type=Path, help="JSON with the board's dimensions")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/" + str(datetime.now()).replace(" ", "_")),
    )
    parser.add_argument(
        "--min-area-mm2",
        type=float,
        help="Minimum candidate area (default: one board square)",
    )
    parser.add_argument(
        "--min-radius-mm",
        type=float,
        help="Smallest glass radius to look for (default: 0.4 board squares)",
    )
    parser.add_argument(
        "--max-radius-mm",
        type=float,
        help="Largest glass radius to look for (default: half the board's short side)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.3,
        help="Ring half-width around the Hough circle, as a fraction of its radius (default: 0.3)",
    )
    args = parser.parse_args()
    try:
        outputs = [
            args.output_dir / name
            for name in ("detections.json", "mask.png", "overlay.png", "highpass.png", "edges.png")
        ]
        inputs = {path.resolve() for path in (args.image, args.board)}
        if any(path.resolve() in inputs for path in outputs):
            raise ValueError("Output paths must not overwrite input files.")
        board = load_board(args.board)
        image = read_image(args.image)
        result, mask, overlay, detail, edges = detect_glass(
            image,
            board,
            args.min_area_mm2,
            args.min_radius_mm,
            args.max_radius_mm,
            args.tolerance,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, output in zip(outputs[1:], (mask, overlay, detail, edges)):
            if not cv2.imwrite(str(path), output):
                raise OSError(f"Could not write image: {path}")
        outputs[0].write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"glass-edges: {error}\n")
    print(f"{len(result['candidates'])} candidate(s); results in {args.output_dir}")
    if not result["candidates"]:
        parser.exit(1, "No glass outline found; inspect highpass.png and edges.png or improve lighting.\n")


if __name__ == "__main__":
    main()
