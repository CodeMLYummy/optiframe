import { LensContour } from './lens';

/** Monocular PDs, from the center of the nose to each pupil, in mm. */
export interface MonocularPd {
  rightMm: number;
  leftMm: number;
}

export const DEFAULT_BRIDGE_MM = 18;
export const MIN_BRIDGE_MM = 10;
export const COMFORT_BRIDGE_MM = { min: 14, max: 24 };

/** Optical centers are assumed at the boxing centers until we can locate them. */
export function bridgeFromPd(right: LensContour, left: LensContour, pd: MonocularPd): number {
  return pd.rightMm - right.aMm / 2 + (pd.leftMm - left.aMm / 2);
}

export function pdFromBridge(right: LensContour, left: LensContour, bridgeMm = DEFAULT_BRIDGE_MM): MonocularPd {
  return { rightMm: bridgeMm / 2 + right.aMm / 2, leftMm: bridgeMm / 2 + left.aMm / 2 };
}

export function splitPd(totalMm: number): MonocularPd {
  return { rightMm: totalMm / 2, leftMm: totalMm / 2 };
}
