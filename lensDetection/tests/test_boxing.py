import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from lensdetection.boxing import measure, measure_box


def ellipse_points(a, b, tilt_degrees=0.0, center=(50.0, 40.0), count=720):
    t = np.linspace(0, 2 * np.pi, count, endpoint=False)
    tilt = np.radians(tilt_degrees)
    x, y = a * np.cos(t), b * np.sin(t)
    return np.stack(
        [
            center[0] + x * np.cos(tilt) - y * np.sin(tilt),
            center[1] + x * np.sin(tilt) + y * np.cos(tilt),
        ],
        axis=1,
    )


class BoxingTests(unittest.TestCase):
    def test_axis_aligned_ellipse(self):
        box = measure_box(ellipse_points(30, 20))
        self.assertAlmostEqual(box["length_mm"], 60, delta=0.05)
        self.assertAlmostEqual(box["width_mm"], 40, delta=0.05)
        self.assertAlmostEqual(box["box_center_board_mm"][0], 50, delta=0.05)
        self.assertAlmostEqual(box["box_center_board_mm"][1], 40, delta=0.05)

    def test_datum_angle_follows_a_tilted_lens(self):
        points = ellipse_points(30, 20, tilt_degrees=25)
        tilted = measure_box(points)
        aligned = measure_box(points, 25)
        self.assertAlmostEqual(aligned["length_mm"], 60, delta=0.05)
        self.assertAlmostEqual(aligned["width_mm"], 40, delta=0.05)
        self.assertLess(tilted["length_mm"], 60)
        self.assertGreater(tilted["width_mm"], 40)
        corners = np.array(aligned["box_corners_board_mm"])
        self.assertAlmostEqual(float(np.linalg.norm(corners[1] - corners[0])), 60, delta=0.05)

    def test_overlay_and_cli(self):
        points = ellipse_points(30, 20)
        homography = np.array([[8, 0, 100], [0, 8, 80], [0, 0, 1]], dtype=np.float64)
        image = np.full((600, 800, 3), 200, np.uint8)
        result, overlay = measure(image, points, homography)
        self.assertEqual(overlay.shape, image.shape)
        self.assertGreater(np.count_nonzero(np.any(overlay != image, axis=2)), 1000)
        self.assertNotIn("frame", result)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "closed.json").write_text(json.dumps({"contour_board_mm": points.tolist()}))
            (folder / "detections.json").write_text(
                json.dumps({"board_to_image_homography": homography.tolist()})
            )
            cv2.imwrite(str(folder / "photo.png"), image)
            run = subprocess.run(
                [sys.executable, "-m", "lensdetection.boxing", str(folder),
                 str(folder / "photo.png")],
                capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            saved = json.loads((folder / "boxing.json").read_text())
            self.assertAlmostEqual(saved["length_mm"], 60, delta=0.05)
            self.assertTrue((folder / "boxing_overlay.png").exists())
            missing = subprocess.run(
                [sys.executable, "-m", "lensdetection.boxing", str(folder / "nope"),
                 str(folder / "photo.png")],
                capture_output=True, text=True,
            )
            self.assertEqual(missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
