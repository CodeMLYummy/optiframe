export type Eye = 'L' | 'R';

/**
 * Lens outline as photographed front (convex) face up, i.e. as seen from the front of the frame.
 * Points in mm, origin at the center of the boxing rectangle, x right, y up, counter-clockwise.
 * Same shape as the backend's LensContour.
 */
export interface LensContour {
  eye: Eye;
  pointsMm: [number, number][];
  aMm: number;
  bMm: number;
  perimeterMm: number;
}

export interface MeasureStep {
  label: string;
  imageDataUrl: string;
}

export interface MeasureResponse {
  contour: LensContour;
  method: string;
  pxPerMm: number;
  markersFound: number;
  reprojectionErrorMm: number;
  sharpness: number;
  rotatedAMm: number;
  rotatedBMm: number;
  steps: MeasureStep[];
  elapsedMs: number;
}

export interface ApiError {
  code: string;
  message: string;
}

/** Test lens, as suggested by the challenge (50 x 36 mm ellipses). */
export function ellipseContour(eye: Eye, aMm = 50, bMm = 36, n = 180): LensContour {
  const pointsMm: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const t = (2 * Math.PI * i) / n;
    pointsMm.push([(aMm / 2) * Math.cos(t), (bMm / 2) * Math.sin(t)]);
  }
  const a = aMm / 2;
  const b = bMm / 2;
  const perimeterMm = Math.PI * (3 * (a + b) - Math.sqrt((3 * a + b) * (a + 3 * b)));
  return { eye, pointsMm, aMm, bMm, perimeterMm };
}
