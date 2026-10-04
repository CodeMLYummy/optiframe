"""Find candidate glass outlines by removing a known ChArUco background."""

import argparse
import json
import math
from datetime import datetime, timezone
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
        if (
            type(data[key]) not in (int, float)
            or not math.isfinite(data[key])
            or data[key] <= 0
        ):
            raise ValueError(f"{key} must be a finite positive number.")
    if data["marker_mm"] >= data["square_mm"]:
        raise ValueError("marker_mm must be smaller than square_mm.")
    name = data["dictionary"]
    if not isinstance(name, str) or name not in DICTIONARIES:
        raise ValueError(
            f"dictionary must be one of: {', '.join(sorted(DICTIONARIES))}"
        )
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARIES[name])
    if data["squares_x"] * data["squares_y"] // 2 > len(dictionary.bytesList):
        raise ValueError("The dictionary does not contain enough marker IDs.")
    if not all(
        math.isfinite(data[key] * data["square_mm"])
        for key in ("squares_x", "squares_y")
    ):
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
    homography, inliers = cv2.findHomography(
        physical, corners.reshape(-1, 2), cv2.RANSAC, 2.0
    )
    if homography is None or inliers is None or int(inliers.sum()) < 6:
        raise ValueError("Could not reliably fit the board plane to the image.")
    selected = inliers.ravel().astype(bool)
    if np.linalg.matrix_rank(physical[selected] - physical[selected].mean(axis=0)) < 2:
        raise ValueError("Inlier corners do not span the board plane.")
    if not np.isfinite(homography).all() or np.linalg.cond(homography) > 1e12:
        raise ValueError("Board homography is degenerate.")
    projected = cv2.perspectiveTransform(physical[selected, None], homography)
    errors = np.linalg.norm(
        projected.reshape(-1, 2) - corners.reshape(-1, 2)[selected], axis=1
    )
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
        raise ValueError(
            "Board squares are too small in the image; use a closer photo."
        )
    tile = max(32, min(256, round(pixels_per_square * 2)))
    template = board.generateImage((sx * tile, sy * tile), marginSize=0, borderBits=1)
    template_to_mm = np.diag([square / tile, square / tile, 1.0])
    transform = homography @ template_to_mm
    height, width = shape
    expected = cv2.warpPerspective(
        template, transform, (width, height), borderValue=255
    )
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


def remove_board_edges(
    observed: np.ndarray,
    expected: np.ndarray,
    footprint: np.ndarray,
    pixels_per_square: float,
    min_score: float = 0.6,
) -> np.ndarray:
    """Return observed edges left after template-matching away the board's edges.

    The rendered board's edge map is cut into tiles. Each tile is matched against
    the observed edge map in a small search window, which absorbs registration
    and lens-distortion drift. Where it matches, the straight printed edges are
    erased, leaving curved edges such as a glass rim.
    """
    observed_edges = cv2.Canny(cv2.GaussianBlur(observed, (5, 5), 1.0), 50, 150)
    expected_edges = cv2.Canny(expected, 50, 150)
    radius = max(2, round(pixels_per_square * 0.08))
    grow = np.ones((3, 3), np.uint8)
    # Pad with the search radius so shifted tiles never leave the arrays.
    observed_map = cv2.copyMakeBorder(
        (cv2.dilate(observed_edges, grow) > 0).astype(np.float32),
        *(radius,) * 4,
        cv2.BORDER_CONSTANT,
    )
    template_map = cv2.copyMakeBorder(
        (expected_edges > 0).astype(np.float32), *(radius,) * 4, cv2.BORDER_CONSTANT
    )
    erase_map = cv2.dilate(template_map, np.ones((5, 5), np.uint8))
    remaining = observed_edges.copy()
    height, width = observed_edges.shape
    tile = max(16, round(pixels_per_square / 2))
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            y1, x1 = min(y + tile, height), min(x + tile, width)
            if cv2.countNonZero(footprint[y:y1, x:x1]) == 0:
                continue
            patch = template_map[radius + y : radius + y1, radius + x : radius + x1]
            expected_pixels = float(patch.sum())
            if expected_pixels < tile * 0.5:
                continue
            window = observed_map[y : y1 + 2 * radius, x : x1 + 2 * radius]
            # Fraction of the board's edge pixels that have an observed edge nearby;
            # extra observed edges (the glass) do not lower it.
            scores = cv2.matchTemplate(window, patch, cv2.TM_CCORR) / expected_pixels
            _, score, _, (left, top) = cv2.minMaxLoc(scores)
            if score < min_score:
                continue
            # (left, top) == (radius, radius) means no shift from the render.
            y0, x0 = y + 2 * radius - top, x + 2 * radius - left
            shifted = erase_map[y0 : y0 + (y1 - y), x0 : x0 + (x1 - x)]
            remaining[y:y1, x:x1][shifted > 0] = 0
    remaining[footprint == 0] = 0
    # Drop short leftovers (printed-edge slivers, noise) that cannot be a rim.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        remaining, connectivity=8
    )
    for label in range(1, count):
        if max(stats[label, cv2.CC_STAT_WIDTH], stats[label, cv2.CC_STAT_HEIGHT]) < (
            pixels_per_square * 0.3
        ):
            remaining[labels == label] = 0
    return remaining


def detect_glass(
    image: np.ndarray,
    board: cv2.aruco.CharucoBoard,
    threshold: float = 30.0,
    min_area_mm2: float | None = None,
    reference: np.ndarray | None = None,
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return candidate contours, a filled mask, overlay, residual, and edge image.

    The edge image holds observed edges that remain after template matching
    removes the ChArUco board's own edges.
    """
    if not math.isfinite(threshold) or not 0 < threshold < 255:
        raise ValueError("Residual threshold must be between 0 and 255.")
    if min_area_mm2 is not None and (
        not math.isfinite(min_area_mm2) or min_area_mm2 <= 0
    ):
        raise ValueError("Minimum area must be finite and positive.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    homography, inlier_count, reprojection_rms = locate_board(gray, board)
    expected, footprint, pixels_per_square = render_background(
        gray.shape, board, homography
    )
    if reference is not None:
        if reference.shape != image.shape:
            raise ValueError(
                "Reference and glass images must have identical dimensions."
            )
        reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        reference_h, _, _ = locate_board(reference_gray, board)
        expected = cv2.warpPerspective(
            reference_gray,
            homography @ np.linalg.inv(reference_h),
            (gray.shape[1], gray.shape[0]),
            borderValue=255,
        )
        reference_valid = cv2.warpPerspective(
            np.full(gray.shape, 255, np.uint8),
            homography @ np.linalg.inv(reference_h),
            (gray.shape[1], gray.shape[0]),
            flags=cv2.INTER_NEAREST,
        )
        footprint = cv2.bitwise_and(footprint, reference_valid)

    observed = cv2.GaussianBlur(gray, (5, 5), 1.0).astype(np.float32)
    background = cv2.GaussianBlur(expected, (5, 5), 1.0).astype(np.float32)
    valid = footprint != 0
    # Robust black/white levels tolerate a minority of glass-covered board pixels.
    dark = valid & (background < 50)
    light = valid & (background > 205)
    if dark.sum() < 50 or light.sum() < 50:
        raise ValueError("Not enough visible black and white board regions.")
    black = float(np.median(observed[dark]))
    white = float(np.median(observed[light]))
    expected_black = float(np.median(background[dark]))
    expected_white = float(np.median(background[light]))
    if white - black < 40:
        raise ValueError("Board contrast is too low for reliable glass detection.")
    gain = (white - black) / (expected_white - expected_black)
    predicted = (background - expected_black) * gain + black
    residual = np.abs(observed - predicted)

    # Registration/antialiasing errors at printed edges are not glass evidence.
    pattern_edges = cv2.Canny(expected, 50, 150)
    pattern_edges = cv2.dilate(pattern_edges, np.ones((3, 3), np.uint8))
    evidence = ((residual >= threshold) & valid & (pattern_edges == 0)).astype(
        np.uint8
    ) * 255
    # Rims that cross a printed edge are recovered from the leftover edges.
    glass_edges = remove_board_edges(gray, expected, footprint, pixels_per_square)
    evidence = cv2.bitwise_or(evidence, glass_edges)
    size = max(3, round(pixels_per_square * 0.12) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    connected = cv2.morphologyEx(evidence, cv2.MORPH_CLOSE, kernel)
    connected = cv2.bitwise_and(connected, footprint)
    contours, _ = cv2.findContours(
        connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    minimum = board.getSquareLength() ** 2 if min_area_mm2 is None else min_area_mm2
    inverse = np.linalg.inv(homography)
    mask = np.zeros(gray.shape, np.uint8)
    overlay = image.copy()
    candidates = []
    border = cv2.subtract(
        footprint,
        cv2.erode(
            footprint,
            np.ones((3, 3), np.uint8),
            borderType=cv2.BORDER_CONSTANT,
            borderValue=0,
        ),
    )
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        if len(contour) < 3:
            continue
        physical = cv2.perspectiveTransform(contour.astype(np.float32), inverse)
        area_mm2 = abs(cv2.contourArea(physical))
        if not math.isfinite(area_mm2) or area_mm2 < minimum:
            continue
        candidate_mask = np.zeros(gray.shape, np.uint8)
        cv2.drawContours(candidate_mask, [contour], -1, 255, cv2.FILLED)
        # Clipped contours have no trustworthy closed boundary.
        if cv2.countNonZero(cv2.bitwise_and(candidate_mask, border)):
            continue
        number = len(candidates) + 1
        cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
        cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 2)
        x, y, width, height = cv2.boundingRect(contour)
        cv2.putText(
            overlay,
            str(number),
            (x, max(15, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
        candidates.append(
            {
                "id": number,
                "contour_px": contour.reshape(-1, 2).tolist(),
                "contour_board_mm": physical.reshape(-1, 2).tolist(),
                "area_mm2": area_mm2,
                "perimeter_mm": float(cv2.arcLength(physical, True)),
                "bounding_box_px": [x, y, width, height],
            }
        )
    residual_image = np.clip(residual, 0, 255).astype(np.uint8)
    residual_image[~valid] = 0
    result = {
        "status": "candidates_found" if candidates else "no_candidates",
        "image_size_px": [gray.shape[1], gray.shape[0]],
        "board_to_image_homography": homography.tolist(),
        "board_inlier_corners": inlier_count,
        "board_reprojection_rms_px": reprojection_rms,
        "residual_threshold": threshold,
        "min_area_mm2": minimum,
        "background_source": "reference" if reference is not None else "rendered_board",
        "candidates": candidates,
    }
    return result, mask, overlay, residual_image, glass_edges


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
    parser.add_argument("--reference", type=Path, help="Optional photo without glass")
    parser.add_argument(
        "--threshold",
        type=float,
        default=30.0,
        help="Grayscale residual threshold (default: 30)",
    )
    parser.add_argument(
        "--min-area-mm2",
        type=float,
        help="Minimum candidate area (default: one board square)",
    )
    args = parser.parse_args()
    try:
        outputs = [
            args.output_dir / name
            for name in ("detections.json", "mask.png", "overlay.png", "residual.png", "edges.png")
        ]
        inputs = {
            path.resolve()
            for path in (args.image, args.board, args.reference)
            if path is not None
        }
        if any(path.resolve() in inputs for path in outputs):
            raise ValueError("Output paths must not overwrite input files.")
        board = load_board(args.board)
        image = read_image(args.image)
        reference = read_image(args.reference) if args.reference is not None else None
        result, mask, overlay, residual, edges = detect_glass(
            image, board, args.threshold, args.min_area_mm2, reference
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, output in zip(outputs[1:], (mask, overlay, residual, edges)):
            if not cv2.imwrite(str(path), output):
                raise OSError(f"Could not write image: {path}")
        outputs[0].write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"glass-edges: {error}\n")
    print(f"{len(result['candidates'])} candidate(s); results in {args.output_dir}")
    if not result["candidates"]:
        parser.exit(
            1, "No glass outline found; inspect residual.png or improve lighting.\n"
        )


if __name__ == "__main__":
    main()
