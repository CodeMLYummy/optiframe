import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np

from lensdetection.ronchi_edges import (
    RonchiPattern, detect_ronchi_glass, load_pattern,
)


class RonchiEdgesTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "width_mm": 20, "height_mm": 15, "bar_width_mm": 0.5,
            "corners_px": [[0, 0], [800, 0], [800, 600], [0, 600]],
        }
        self.pattern = RonchiPattern(
            20, 15, 0.5, np.array(self.config["corners_px"], dtype=np.float32)
        )
        gray = np.tile(
            np.where((np.arange(801) // 20) % 2, 255, 0).astype(np.uint8),
            (601, 1),
        )
        self.bare = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        self.glass = self.bare.copy()
        cv2.ellipse(self.glass, (400, 300), (140, 105), 12, 0, 360,
                    (110, 110, 110), 6)
        self.truth = np.zeros(gray.shape, np.uint8)
        cv2.ellipse(self.truth, (400, 300), (140, 105), 12, 0, 360, 255, -1)

    def assert_outline(self, mask, truth):
        intersection = np.count_nonzero((mask > 0) & (truth > 0))
        union = np.count_nonzero((mask > 0) | (truth > 0))
        self.assertGreater(intersection / union, 0.85)

    def test_bare_pattern(self):
        result, images = detect_ronchi_glass(self.bare, self.pattern)
        self.assertEqual(result["status"], "no_candidates")
        self.assertEqual(cv2.countNonZero(images["mask.png"]), 0)

    def test_rim_and_measurements(self):
        result, images = detect_ronchi_glass(self.glass, self.pattern)
        self.assertEqual(len(result["candidates"]), 1)
        self.assert_outline(images["mask.png"], self.truth)
        candidate = result["candidates"][0]
        expected_area = np.pi * 140 * 105 / 40**2
        self.assertAlmostEqual(candidate["area_mm2"], expected_area,
                               delta=expected_area * 0.1)
        physical = np.array(candidate["contour_pattern_mm"])
        self.assertAlmostEqual(
            (physical[:, 0].max() + physical[:, 0].min()) / 2, 10, delta=0.1
        )
        self.assertGreater(cv2.countNonZero(images["edges.png"]), 0)

    def test_perspective_and_exposure(self):
        corners = np.array([[70, 60], [870, 100], [820, 720], [100, 680]],
                           dtype=np.float32)
        transform = cv2.getPerspectiveTransform(self.pattern.corners_px, corners)
        pattern = RonchiPattern(20, 15, 0.5, corners)
        for has_glass in (False, True):
            with self.subTest(has_glass=has_glass):
                photo = cv2.warpPerspective(
                    self.glass if has_glass else self.bare,
                    transform, (960, 800), borderValue=(255, 255, 255),
                )
                photo = (photo.astype(np.float32) * 0.8 + 20).astype(np.uint8)
                result, images = detect_ronchi_glass(photo, pattern)
                self.assertEqual(len(result["candidates"]), int(has_glass))
                if has_glass:
                    truth = cv2.warpPerspective(self.truth, transform, (960, 800))
                    self.assert_outline(images["mask.png"], truth)

    def test_reference(self):
        # A vertical lighting gradient is not represented by a column median.
        gradient = np.linspace(0.65, 1, 601)[:, None, None]
        reference = (self.bare * gradient).astype(np.uint8)
        photo = (self.glass * gradient).astype(np.uint8)
        result, images = detect_ronchi_glass(
            photo, self.pattern, reference=reference
        )
        self.assertEqual(result["background_source"], "reference")
        self.assertEqual(len(result["candidates"]), 1)
        self.assert_outline(images["mask.png"], self.truth)
        result, _ = detect_ronchi_glass(reference, self.pattern, reference=reference)
        self.assertEqual(result["candidates"], [])

    def test_horizontal_bars_with_rotated_corner_order(self):
        photo = cv2.rotate(self.glass, cv2.ROTATE_90_CLOCKWISE)
        truth = cv2.rotate(self.truth, cv2.ROTATE_90_CLOCKWISE)
        pattern = RonchiPattern(
            20, 15, 0.5,
            np.array([[600, 0], [600, 800], [0, 800], [0, 0]], dtype=np.float32),
        )
        result, images = detect_ronchi_glass(photo, pattern)
        self.assertEqual(len(result["candidates"]), 1)
        self.assert_outline(images["mask.png"], truth)

    def test_stripe_displacement(self):
        photo = self.bare.copy()
        shifted = np.roll(self.bare, 8, axis=1)
        photo[self.truth > 0] = shifted[self.truth > 0]
        result, images = detect_ronchi_glass(photo, self.pattern)
        self.assertEqual(len(result["candidates"]), 1)
        self.assert_outline(images["mask.png"], self.truth)

    def test_area_filter_and_clipped_rim(self):
        result, _ = detect_ronchi_glass(self.glass, self.pattern, min_area_mm2=100)
        self.assertEqual(result["candidates"], [])
        photo = self.bare.copy()
        cv2.ellipse(photo, (30, 300), (140, 105), 0, 0, 360,
                    (110, 110, 110), 6)
        result, _ = detect_ronchi_glass(photo, self.pattern)
        self.assertEqual(result["candidates"], [])

    def test_bad_pattern_and_parameters(self):
        with self.assertRaisesRegex(ValueError, "contrast"):
            detect_ronchi_glass(np.full_like(self.bare, 255), self.pattern)
        wrong = RonchiPattern(20, 15, 0.8, self.pattern.corners_px)
        with self.assertRaisesRegex(ValueError, "do not match"):
            detect_ronchi_glass(self.bare, wrong)
        outside = RonchiPattern(20, 15, 0.5, self.pattern.corners_px + 100)
        with self.assertRaisesRegex(ValueError, "inside"):
            detect_ronchi_glass(self.bare, outside)
        for threshold in (0, 255, float("nan"), float("inf")):
            with self.subTest(threshold=threshold):
                with self.assertRaisesRegex(ValueError, "Threshold"):
                    detect_ronchi_glass(self.bare, self.pattern, threshold=threshold)
        with self.assertRaisesRegex(ValueError, "Minimum area"):
            detect_ronchi_glass(self.bare, self.pattern, min_area_mm2=-1)
        with self.assertRaisesRegex(ValueError, "identical dimensions"):
            detect_ronchi_glass(self.bare, self.pattern, reference=self.bare[:400])

    def test_json_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "pattern.json"
            config.write_text(json.dumps(self.config))
            pattern = load_pattern(config)
            self.assertEqual(pattern.bar_width_mm, 0.5)
            image = root / "photo.png"
            output = root / "output"
            for photo, status in ((self.glass, 0), (self.bare, 1)):
                cv2.imwrite(str(image), photo)
                completed = subprocess.run(
                    [sys.executable, "-m", "lensdetection.ronchi_edges",
                     str(image), str(config), "--output-dir", str(output)],
                    capture_output=True, text=True,
                )
                self.assertEqual(completed.returncode, status, completed.stderr)
                data = json.loads((output / "detections.json").read_text())
                self.assertEqual(bool(data["candidates"]), status == 0)
                for name in ("mask.png", "edges.png", "overlay.png",
                             "rectified.png", "residual.png"):
                    self.assertIsNotNone(cv2.imread(str(output / name)))
            invalid = [
                [], {}, dict(self.config, width_mm=True),
                dict(self.config, bar_width_mm=0),
                dict(self.config, height_mm="15"),
                dict(self.config, corners_px=[[0, 0]] * 4),
                dict(self.config, corners_px=[[0, 0], [0, 600], [800, 600], [800, 0]]),
                dict(self.config, corners_px=[[0, 0], [800, 600], [800, 0], [0, 600]]),
            ]
            for data in invalid:
                with self.subTest(data=data):
                    config.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        load_pattern(config)
            completed = subprocess.run(
                [sys.executable, "-m", "lensdetection.ronchi_edges",
                 str(image), str(config), "--output-dir", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertNotIn("Traceback", completed.stderr)
            config.write_text(json.dumps(self.config))
            # Input/output collision must be refused before touching the photo.
            collision = output / "overlay.png"
            before = collision.read_bytes()
            completed = subprocess.run(
                [sys.executable, "-m", "lensdetection.ronchi_edges",
                 str(collision), str(config), "--output-dir", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("overwrite", completed.stderr)
            self.assertEqual(collision.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
