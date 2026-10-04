import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from lensdetection.glass_edges import detect_glass, load_board


class GlassEdgesTests(unittest.TestCase):
    def setUp(self):
        self.board = cv2.aruco.CharucoBoard(
            (8, 6),
            25.0,
            18.0,
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
        )
        gray = self.board.generateImage((800, 600))
        self.bare = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        self.glass = self.bare.copy()
        cv2.ellipse(self.glass, (400, 300), (140, 105), 12, 0, 360, (110, 110, 110), 6)
        self.truth = np.zeros(gray.shape, np.uint8)
        cv2.ellipse(self.truth, (400, 300), (140, 105), 12, 0, 360, 255, -1)

    def assert_outline(self, mask, truth):
        intersection = np.count_nonzero((mask > 0) & (truth > 0))
        union = np.count_nonzero((mask > 0) | (truth > 0))
        self.assertGreater(intersection / union, 0.85)

    def test_bare_board_has_no_candidates(self):
        result, mask, _, _, _ = detect_glass(self.bare, self.board)
        self.assertEqual(result["status"], "no_candidates")
        self.assertEqual(cv2.countNonZero(mask), 0)

    def test_glass_rim_and_physical_coordinates(self):
        result, mask, overlay, detail, edges = detect_glass(self.glass, self.board)
        self.assertEqual(len(result["candidates"]), 1)
        self.assert_outline(mask, self.truth)
        candidate = result["candidates"][0]
        expected_area = np.pi * 140 * 105 * (25 / 100) ** 2
        self.assertAlmostEqual(candidate["area_mm2"], expected_area, delta=expected_area * 0.1)
        physical = np.array(candidate["contour_board_mm"])
        self.assertAlmostEqual((physical[:, 0].max() + physical[:, 0].min()) / 2, 100, delta=1)
        self.assertAlmostEqual((physical[:, 1].max() + physical[:, 1].min()) / 2, 75, delta=1)
        self.assertEqual(overlay.shape, self.glass.shape)
        self.assertEqual(detail.shape, self.truth.shape)
        self.assertEqual(edges.shape, self.truth.shape)

    def test_perspective_and_brightness(self):
        transform = cv2.getPerspectiveTransform(
            np.array([[0, 0], [799, 0], [799, 599], [0, 599]], dtype=np.float32),
            np.array([[80, 70], [880, 110], [820, 720], [120, 680]], dtype=np.float32),
        )
        for has_glass in (False, True):
            with self.subTest(has_glass=has_glass):
                photo = cv2.warpPerspective(
                    self.glass if has_glass else self.bare,
                    transform,
                    (960, 800),
                    borderValue=(255, 255, 255),
                )
                photo = (photo.astype(np.float32) * 0.8 + 20).astype(np.uint8)
                result, mask, _, _, _ = detect_glass(photo, self.board)
                if has_glass:
                    truth = cv2.warpPerspective(self.truth, transform, (960, 800))
                    self.assertEqual(len(result["candidates"]), 1)
                    self.assert_outline(mask, truth)
                else:
                    self.assertEqual(result["candidates"], [])

    def test_ellipse_fit_and_isolated_edges(self):
        result, _, _, _, edges = detect_glass(self.glass, self.board)
        circle = result["hough_circle"]
        self.assertAlmostEqual(circle["center_px"][0], 400, delta=20)
        self.assertAlmostEqual(circle["center_px"][1], 300, delta=20)
        ellipse = circle["ellipse"]
        self.assertAlmostEqual(ellipse["center_px"][0], 400, delta=3)
        self.assertAlmostEqual(ellipse["center_px"][1], 300, delta=3)
        self.assertAlmostEqual(max(ellipse["axes_px"]), 280, delta=12)
        self.assertAlmostEqual(min(ellipse["axes_px"]), 210, delta=12)
        ys, xs = np.nonzero(edges)
        self.assertGreater(len(xs), 500)
        rim = np.zeros_like(edges)
        cv2.ellipse(rim, (400, 300), (140, 105), 12, 0, 360, 255, 1)
        distance = cv2.distanceTransform(255 - rim, cv2.DIST_L2, 3)
        self.assertLess(distance[ys, xs].max(), 15)

    def test_minimum_area_filters_candidates(self):
        result, mask, _, _, _ = detect_glass(self.glass, self.board, min_area_mm2=5000)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(cv2.countNonZero(mask), 0)

    def test_clipped_outline_is_rejected(self):
        photo = self.bare.copy()
        cv2.ellipse(photo, (30, 300), (140, 105), 0, 0, 360, (110, 110, 110), 6)
        result, mask, _, _, _ = detect_glass(photo, self.board)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(cv2.countNonZero(mask), 0)

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "six visible"):
            detect_glass(np.full_like(self.bare, 255), self.board)
        with self.assertRaisesRegex(ValueError, "Minimum area"):
            detect_glass(self.glass, self.board, min_area_mm2=-1)
        with self.assertRaisesRegex(ValueError, "Ring tolerance"):
            detect_glass(self.glass, self.board, tolerance=1.5)
        with self.assertRaisesRegex(ValueError, "Minimum radius"):
            detect_glass(self.glass, self.board, min_radius_mm=50, max_radius_mm=20)

    def test_board_json_validation(self):
        config = {
            "squares_x": 8,
            "squares_y": 6,
            "square_mm": 25,
            "marker_mm": 18,
            "dictionary": "4X4_50",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.json"
            path.write_text(json.dumps(config))
            board = load_board(path)
            self.assertEqual(board.getChessboardSize(), (8, 6))
            invalid = [
                [],
                {},
                dict(config, squares_x=True),
                dict(config, marker_mm=25),
                dict(config, square_mm="25"),
                dict(config, dictionary="unknown"),
                dict(config, squares_x=20, squares_y=20),
            ]
            for value in invalid:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    with self.assertRaises(ValueError):
                        load_board(path)

    def test_cli_outputs_and_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "board.json"
            config.write_text(
                json.dumps(
                    {
                        "squares_x": 8,
                        "squares_y": 6,
                        "square_mm": 25,
                        "marker_mm": 18,
                        "dictionary": "4X4_50",
                    }
                )
            )
            image = root / "photo.png"
            output = root / "output"
            for photo, expected_status in ((self.glass, 0), (self.bare, 1)):
                with self.subTest(expected_status=expected_status):
                    self.assertTrue(cv2.imwrite(str(image), photo))
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "lensdetection.glass_edges",
                            str(image),
                            str(config),
                            "--output-dir",
                            str(output),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(completed.returncode, expected_status, completed.stderr)
                    data = json.loads((output / "detections.json").read_text())
                    self.assertEqual(bool(data["candidates"]), expected_status == 0)
                    for name in (
                        "overlay.png",
                        "mask.png",
                        "highpass.png",
                        "edges.png",
                    ):
                        self.assertIsNotNone(cv2.imread(str(output / name)))


if __name__ == "__main__":
    unittest.main()
