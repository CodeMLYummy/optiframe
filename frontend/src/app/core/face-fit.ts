/**
 * Places the frame on a face from MediaPipe Face Landmarker's 478 landmarks (with irises). The scale comes from the
 * iris: its visible diameter is about the same in all adults (11.7 mm, horizontal visible iris diameter), so the
 * preview is at true size without any reference object, to within about 5 %.
 */
export const IRIS_DIAMETER_MM = 11.7;

/** First landmark of each iris: its centre, followed by 4 points on its edge (right, top, left, bottom). */
const IRISES = [468, 473];

export interface Landmark {
  x: number;
  y: number;
}

export interface FacePlacement {
  /** Midpoint between the pupils, in image pixels. */
  x: number;
  y: number;
  /** Tilt of the line between the pupils, degrees, clockwise in the image. */
  rollDeg: number;
  pxPerMm: number;
  /** Pupillary distance estimated from the iris scale. */
  pdMm: number;
}

/** Null when the landmarks have no irises. Landmarks are normalized to the image size, as MediaPipe returns them. */
export function placeOnFace(landmarks: readonly Landmark[], width: number, height: number): FacePlacement | null {
  if (landmarks.length < 478) {
    return null;
  }
  const px = (i: number): [number, number] => [landmarks[i].x * width, landmarks[i].y * height];
  const dist = (a: number, b: number) => Math.hypot(px(a)[0] - px(b)[0], px(a)[1] - px(b)[1]);
  const diameters = IRISES.map((c) => (dist(c + 1, c + 3) + dist(c + 2, c + 4)) / 2);
  const pxPerMm = (diameters[0] + diameters[1]) / 2 / IRIS_DIAMETER_MM;
  // The image's left pupil first, so the angle is the tilt of the face whichever iris MediaPipe lists first.
  const [a, b] = IRISES.map(px).sort((p, q) => p[0] - q[0]);
  const pupils = Math.hypot(b[0] - a[0], b[1] - a[1]);
  return {
    x: (a[0] + b[0]) / 2,
    y: (a[1] + b[1]) / 2,
    rollDeg: (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI,
    pxPerMm,
    pdMm: pupils / pxPerMm,
  };
}
