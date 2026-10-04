import cv2
from common import BBOX, load

for n, b in BBOX.items():
    im = load(n)
    x, y, w, h = b
    cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 6)
    cv2.imwrite(f"view_{n}.jpg", cv2.resize(im, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))
