import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from lensdetection.close_contour import close_contour
from lensdetection.glass_edges import detect_glass


class CloseContourTests(unittest.TestCase):
    def setUp(self):
        board = cv2.aruco.CharucoBoard(
            (8, 6),
            25.0,
            18.0,
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
        )
        self.photo = cv2.cvtColor(board.generateImage((800, 600)), cv2.COLOR_GRAY2BGR)
        cv2.ellipse(self.photo, (400, 300), (140, 105), 12, 0, 360, (110, 110, 110), 6)
        self.truth = np.zeros((600, 800), np.uint8)
        cv2.ellipse(self.truth, (400, 300), (140, 105), 12, 0, 360, 255, -1)
        result, _, _, self.detail, self.edges = detect_glass(self.photo, board)
        self.detections = json.loads(json.dumps(result))

    def iou(self, mask):
        union = np.count_nonzero((mask > 0) | (self.truth > 0))
        return np.count_nonzero((mask > 0) & (self.truth > 0)) / union

    def open_edges(self):
        opened = self.edges.copy()
        # Remove a 70 degree arc of the rim.
        ys, xs = np.nonzero(opened)
        angle = np.degrees(np.arctan2(ys - 300, xs - 400))
        opened[ys[(angle > 20) & (angle < 90)], xs[(angle > 20) & (angle < 90)]] = 0
        return opened

    def test_closed_rim_is_reproduced(self):
        result, mask, overlay, detail_overlay, svg = close_contour(
            self.edges, self.detections, self.photo, detail=self.detail
        )
        self.assertEqual(result["status"], "closed")
        self.assertGreater(self.iou(mask), 0.9)
        self.assertEqual(overlay.shape, self.photo.shape)
        self.assertEqual(detail_overlay.shape, self.photo.shape)
        # Drawn over the high-pass image, so it differs from the photo overlay.
        self.assertFalse(np.array_equal(overlay, detail_overlay))
        green = np.all(detail_overlay == (0, 255, 0), axis=2)
        self.assertGreater(np.count_nonzero(green), 500)
        self.assertTrue(svg.startswith("<svg") and "C " in svg and " Z" in svg)

    def test_gap_is_bridged_with_a_closed_spline(self):
        opened = self.open_edges()
        result, mask, _, _, _ = close_contour(opened, self.detections)
        self.assertEqual(result["status"], "closed")
        self.assertLess(result["measured_fraction"], 0.9)
        self.assertGreater(len(result["bridged_segments"]), 3)
        self.assertGreater(self.iou(mask), 0.85)
        segments = np.array(result["bezier_px"])
        self.assertTrue(np.allclose(segments[:, 3], np.roll(segments[:, 0], -1, axis=0)))
        expected_area = np.pi * 140 * 105 * (25 / 100) ** 2
        self.assertAlmostEqual(result["area_mm2"], expected_area, delta=expected_area * 0.1)

    def test_too_open_and_invalid_inputs(self):
        sparse = np.zeros_like(self.edges)
        sparse[self.open_edges() > 0] = 255
        ys, xs = np.nonzero(sparse)
        angle = np.degrees(np.arctan2(ys - 300, xs - 400))
        drop = angle > -90
        sparse[ys[drop], xs[drop]] = 0
        result, _, _, _, _ = close_contour(sparse, self.detections)
        self.assertEqual(result["status"], "too_open")
        with self.assertRaisesRegex(ValueError, "Too few"):
            close_contour(np.zeros_like(self.edges), self.detections)
        with self.assertRaisesRegex(ValueError, "identical dimensions"):
            close_contour(self.edges, self.detections, self.photo[:400])
        with self.assertRaisesRegex(ValueError, "knots"):
            close_contour(self.edges, self.detections, knots=3)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cv2.imwrite(str(root / "edges.png"), self.open_edges())
            cv2.imwrite(str(root / "highpass.png"), self.detail)
            (root / "detections.json").write_text(json.dumps(self.detections))
            command = [sys.executable, "-m", "lensdetection.close_contour", str(root)]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for name in (
                "closed.json",
                "closed.svg",
                "closed_mask.png",
                "closed_overlay.png",
                "closed_highpass_overlay.png",
            ):
                self.assertTrue((root / name).exists(), name)
            (root / "detections.json").write_text("{}")
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
