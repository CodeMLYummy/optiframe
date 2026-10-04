"""ArUco dictionaries shared by the board generator and image detector."""

import cv2

DICTIONARIES = {
    name.removeprefix("DICT_"): getattr(cv2.aruco, name) for name in dir(cv2.aruco) if name.startswith("DICT_")
}
