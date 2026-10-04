import { contourSvg, lensPairSvg } from './exports';
import { LensContour, ellipseContour } from './lens';

describe('contourSvg', () => {
  it('is sized in mm so it prints at 1:1', () => {
    const svg = contourSvg(ellipseContour('R', 50, 36));
    // 50 mm lens + 2 x 10 mm margin.
    expect(svg).toContain('width="70.000mm"');
    expect(svg).toContain('height="56.000mm"');
    expect(svg).toContain('viewBox="0 0 70.000 56.000"');
  });

  describe('lensPairSvg', () => {
    it('exports both lenses in one millimetre-sized SVG with a matching viewBox', () => {
      const svg = lensPairSvg(ellipseContour('R', 50, 36), ellipseContour('L', 60, 40));
      const document = new DOMParser().parseFromString(svg, 'image/svg+xml');
      const root = document.documentElement;

      expect(document.querySelector('parsererror')).toBeNull();
      expect(document.querySelectorAll('svg')).toHaveLength(1);
      expect(document.querySelectorAll('path')).toHaveLength(2);
      expect(root.getAttribute('width')).toBe('140.000mm');
      expect(root.getAttribute('height')).toBe('65.000mm');
      expect(root.getAttribute('viewBox')).toBe('0 0 140.000 65.000');
      expect(document.querySelectorAll('text')[0].textContent).toContain('OD (droit)');
      expect(document.querySelectorAll('text')[1].textContent).toContain('OG (gauche)');
    });

    it('only translates and flips y, preserving asymmetric outlines and their measured perimeter', () => {
      const right: LensContour = {
        eye: 'R',
        pointsMm: [
          [-20, -10],
          [30, -10],
          [15, 20],
        ],
        aMm: 50,
        bMm: 30,
        perimeterMm: 0,
      };
      const left: LensContour = {
        eye: 'L',
        pointsMm: [
          [-15, -25],
          [25, -15],
          [-5, 15],
        ],
        aMm: 40,
        bMm: 40,
        perimeterMm: 0,
      };
      const svg = lensPairSvg(right, left);
      const document = new DOMParser().parseFromString(svg, 'image/svg+xml');
      const paths = [...document.querySelectorAll('path')];

      for (const [index, lens] of [right, left].entries()) {
        const d = paths[index].getAttribute('d')!;
        expect(d.endsWith(' Z')).toBe(true);
        const points = [...d.matchAll(/[ML](-?\d+\.\d+) (-?\d+\.\d+)/g)].map((match) => [
          Number(match[1]),
          Number(match[2]),
        ]);
        expect(points).toHaveLength(lens.pointsMm.length);
        const offsetX = points[0][0] - lens.pointsMm[0][0];
        const offsetY = points[0][1] + lens.pointsMm[0][1];
        let originalPerimeter = 0;
        let exportedPerimeter = 0;
        points.forEach(([x, y], i) => {
          expect(x).toBeCloseTo(lens.pointsMm[i][0] + offsetX, 3);
          expect(y).toBeCloseTo(offsetY - lens.pointsMm[i][1], 3);
          const next = (i + 1) % points.length;
          originalPerimeter += Math.hypot(
            lens.pointsMm[next][0] - lens.pointsMm[i][0],
            lens.pointsMm[next][1] - lens.pointsMm[i][1],
          );
          exportedPerimeter += Math.hypot(points[next][0] - x, points[next][1] - y);
        });
        expect(exportedPerimeter).toBeCloseTo(originalPerimeter, 3);
      }
      expect(paths[0].getAttribute('d')).toBe('M10.000 40.000 L60.000 40.000 L45.000 10.000 Z');
      expect(paths[1].getAttribute('d')).toBe('M70.000 55.000 L110.000 45.000 L80.000 15.000 Z');
    });
  });
});
