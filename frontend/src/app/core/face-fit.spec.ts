import { describe, expect, it } from 'vitest';

import { IRIS_DIAMETER_MM, Landmark, placeOnFace } from './face-fit';

/** 478 landmarks with two irises of the given pixel diameter, pupils at (x1, y1) and (x2, y2), in a 1000 px image. */
function face(x1: number, y1: number, x2: number, y2: number, irisPx: number): Landmark[] {
  const lm: Landmark[] = Array.from({ length: 478 }, () => ({ x: 0, y: 0 }));
  const r = irisPx / 2;
  for (const [c, x, y] of [
    [468, x1, y1],
    [473, x2, y2],
  ]) {
    const pts = [
      [x, y],
      [x + r, y],
      [x, y - r],
      [x - r, y],
      [x, y + r],
    ];
    pts.forEach(([px, py], i) => (lm[c + i] = { x: px / 1000, y: py / 1000 }));
  }
  return lm;
}

describe('placeOnFace', () => {
  it('scales from the iris and measures the PD', () => {
    const ppm = 4;
    const p = placeOnFace(face(400, 500, 400 + 63 * ppm, 500, IRIS_DIAMETER_MM * ppm), 1000, 1000)!;
    expect(p.pxPerMm).toBeCloseTo(ppm);
    expect(p.pdMm).toBeCloseTo(63);
    expect(p.x).toBeCloseTo(400 + 31.5 * ppm);
    expect(p.rollDeg).toBeCloseTo(0);
  });

  it('gives the tilt whichever iris comes first', () => {
    const p = placeOnFace(face(600, 600, 400, 400, 40), 1000, 1000)!;
    expect(p.rollDeg).toBeCloseTo(45);
  });

  it('needs the iris landmarks', () => {
    expect(placeOnFace([], 100, 100)).toBeNull();
  });
});
