import { describe, expect, it } from 'vitest';

import { gap, signedDistance, spread } from './coherence';
import { ellipseContour } from './lens';

const square = (half: number): [number, number][] => [
  [-half, -half],
  [half, -half],
  [half, half],
  [-half, half],
];

describe('coherence', () => {
  it('signs the distance: inside positive, outside negative', () => {
    expect(signedDistance([0, 0], square(10))).toBeCloseTo(10);
    expect(signedDistance([12, 0], square(10))).toBeCloseTo(-2);
  });

  it('measures a constant gap to an outline offset outward', () => {
    const g = gap(square(10), square(11.2));
    expect(g.minMm).toBeCloseTo(1.2);
    expect(g.maxMm).toBeCloseTo(1.2);
  });

  it('measures the overlap of an outline inside the lens as negative', () => {
    const edgeMidpoints: [number, number][] = [
      [10, 0],
      [0, 10],
      [-10, 0],
      [0, -10],
    ];
    expect(gap(edgeMidpoints, square(9)).meanMm).toBeCloseTo(-1);
  });

  it('gives the spread of A and B between takes', () => {
    const s = spread([
      ellipseContour('R', 50, 36),
      ellipseContour('R', 50.4, 35.7),
      ellipseContour('R', 49.8, 36),
    ]);
    expect(s.takes).toBe(3);
    expect(s.aMm).toBeCloseTo(0.6);
    expect(s.bMm).toBeCloseTo(0.3);
  });
});
