import { contourSvg } from './exports';
import { ellipseContour } from './lens';

describe('contourSvg', () => {
  it('is sized in mm so it prints at 1:1', () => {
    const svg = contourSvg(ellipseContour('R', 50, 36));
    // 50 mm lens + 2 x 10 mm margin.
    expect(svg).toContain('width="70.000mm"');
    expect(svg).toContain('height="56.000mm"');
    expect(svg).toContain('viewBox="0 0 70.000 56.000"');
  });
});
