import { LensContour } from './lens';

type Pt = readonly [number, number];

/** Accuracy the challenge asks for on A and B. */
export const JURY_TOLERANCE_MM = 1;

export interface GapStats {
  minMm: number;
  meanMm: number;
  maxMm: number;
}

/** Distance from p to the closed polygon's outline, positive when p is inside it. */
export function signedDistance(p: Pt, poly: readonly Pt[]): number {
  let best = Infinity;
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ax, ay] = poly[j];
    const [bx, by] = poly[i];
    const ex = bx - ax;
    const ey = by - ay;
    const len2 = ex * ex + ey * ey;
    const t = len2 ? Math.max(0, Math.min(1, ((p[0] - ax) * ex + (p[1] - ay) * ey) / len2)) : 0;
    best = Math.min(best, Math.hypot(p[0] - (ax + t * ex), p[1] - (ay + t * ey)));
    if (ay > p[1] !== by > p[1] && p[0] < ax + ((p[1] - ay) * ex) / ey) {
      inside = !inside;
    }
  }
  return inside ? best : -best;
}

/**
 * Gap between the lens contour and an outline of the frame, measured from every contour point: positive when the
 * outline is outside the lens (the groove), negative when it is inside (the lip covering the lens edge).
 */
export function gap(contour: readonly Pt[], outline: readonly Pt[]): GapStats {
  const d = contour.map((p) => signedDistance(p, outline));
  return {
    minMm: Math.min(...d),
    meanMm: d.reduce((s, v) => s + v, 0) / d.length,
    maxMm: Math.max(...d),
  };
}

export interface TakesSpread {
  takes: number;
  /** Largest difference between two takes. */
  aMm: number;
  bMm: number;
}

/** Spread of A and B over several photos of the same lens. */
export function spread(takes: readonly LensContour[]): TakesSpread {
  const range = (v: number[]) => Math.max(...v) - Math.min(...v);
  return {
    takes: takes.length,
    aMm: range(takes.map((t) => t.aMm)),
    bMm: range(takes.map((t) => t.bMm)),
  };
}
