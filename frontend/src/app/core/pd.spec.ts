import { ellipseContour } from './lens';
import { bridgeFromPd, pdFromBridge, splitPd } from './pd';

describe('PD and bridge', () => {
  const right = ellipseContour('R', 50, 36);
  const left = ellipseContour('L', 46, 40);

  it('derives the bridge from a binocular PD', () => {
    // 64 - (50 + 46) / 2
    expect(bridgeFromPd(right, left, splitPd(64))).toBeCloseTo(16);
  });

  it('uses each monocular PD on its own side', () => {
    // (31 - 25) + (33 - 23)
    expect(bridgeFromPd(right, left, { rightMm: 31, leftMm: 33 })).toBeCloseTo(16);
  });

  it('round-trips with the bridge fallback', () => {
    expect(bridgeFromPd(right, left, pdFromBridge(right, left, 18))).toBeCloseTo(18);
  });
});
