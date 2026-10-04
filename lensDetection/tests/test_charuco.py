import unittest

from lensdetection.charuco import parse_xrandr_monitors, select_monitor


XRANDR_OUTPUT = """\
Monitors: 2
 0: +*eDP-1 1920/340x1080/190+0+0  eDP-1
 1: +DP-1 2560/600x1440/340-2560+0  DP-1
"""


class CharucoDisplayTests(unittest.TestCase):
    def test_parses_active_monitor_geometry(self):
        monitors = parse_xrandr_monitors(XRANDR_OUTPUT)

        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0].name, "eDP-1")
        self.assertEqual(monitors[0].width_px, 1920)
        self.assertEqual(monitors[0].width_mm, 340)
        self.assertTrue(monitors[0].primary)
        self.assertEqual(monitors[1].x, -2560)

    def test_selects_monitor_under_pointer(self):
        monitors = parse_xrandr_monitors(XRANDR_OUTPUT)

        self.assertEqual(select_monitor(monitors, (-100, 500)).name, "DP-1")
        self.assertEqual(select_monitor(monitors, (100, 500)).name, "eDP-1")

    def test_falls_back_to_primary_monitor(self):
        monitors = parse_xrandr_monitors(XRANDR_OUTPUT)

        self.assertEqual(select_monitor(monitors, None).name, "eDP-1")

    def test_does_not_guess_between_non_primary_monitors(self):
        monitors = [
            monitor.__class__(
                monitor.name,
                monitor.width_px,
                monitor.width_mm,
                monitor.height_px,
                monitor.x,
                monitor.y,
                False,
            )
            for monitor in parse_xrandr_monitors(XRANDR_OUTPUT)
        ]

        self.assertIsNone(select_monitor(monitors, None))


if __name__ == "__main__":
    unittest.main()
