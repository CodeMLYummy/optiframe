import Module, { CrossSection, Manifold, ManifoldToplevel, Vec2 } from 'manifold-3d';
import { BufferAttribute, BufferGeometry } from 'three';

import { LensContour } from './lens';
import { MonocularPd } from './pd';

/**
 * Model coordinates, in mm: x to the right and y up as seen from the front of the glasses,
 * z toward the viewer. The front face is at z = thickness, the back face at z = 0, the hinge lugs go to z < 0.
 * The right lens (R) sits on the viewer's left (x < 0).
 */
export interface FrameParams {
  /** Gap between the lens outline and the bottom of the groove. */
  clearanceMm: number;
  /** How far the V-groove goes beyond the lens outline (holds the lens bevel). */
  grooveDepthMm: number;
  /** Material outside the groove. */
  rimWidthMm: number;
  thicknessMm: number;
  /** Lip on the front face that stops the lens. */
  frontLipMm: number;
  /** Smaller lip on the back face: the lens snaps past it. */
  backLipMm: number;
}

export const DEFAULT_FRAME: FrameParams = {
  clearanceMm: 0.2,
  grooveDepthMm: 1,
  rimWidthMm: 3,
  thicknessMm: 5,
  frontLipMm: 1,
  backLipMm: 0.4,
};

const SLICE_MM = 0.25;
const LUG = { widthMm: 4, heightMm: 8, depthMm: 6, pinDiameterMm: 1.6 };

export interface FrameResult {
  /** Model coordinates, for the preview. */
  geometry: BufferGeometry;
  /** Same mesh rotated front face down on the bed, ready to print. */
  printGeometry: BufferGeometry;
  /** Inner outline at the bottom of the groove, per lens, in model coordinates (for the coherence overlay). */
  grooveOutlines: { eye: LensContour['eye']; pointsMm: Vec2[] }[];
  /** Through holes of the printed part: 2 lens openings + 2 pin holes. */
  genus: number;
  triangles: number;
  volumeMm3: number;
}

let toplevel: Promise<ManifoldToplevel> | undefined;

function loadManifold(): Promise<ManifoldToplevel> {
  toplevel ??= Module({ locateFile: () => new URL('manifold.wasm', document.baseURI).href }).then((m) => {
    m.setup();
    return m;
  });
  return toplevel;
}

/** Each lens's boxing center is placed at its monocular PD from the frame center. */
export async function generateFrame(
  right: LensContour,
  left: LensContour,
  pd: MonocularPd,
  p: FrameParams = DEFAULT_FRAME,
): Promise<FrameResult> {
  const { CrossSection, Manifold } = await loadManifold();
  const garbage: { delete(): void }[] = [];
  const keep = <T extends { delete(): void }>(x: T): T => {
    garbage.push(x);
    return x;
  };

  try {
    const T = p.thicknessMm;
    const grooveOffset = p.clearanceMm + p.grooveDepthMm;
    const lenses = [
      { lens: right, cx: -pd.rightMm },
      { lens: left, cx: pd.leftMm },
    ];

    const solids: Manifold[] = [];
    const holes: Manifold[] = [];
    const grooveOutlines: FrameResult['grooveOutlines'] = [];
    const rims: CrossSection[] = [];

    for (const { lens, cx } of lenses) {
      const outline = keep(new CrossSection([lens.pointsMm as Vec2[]]).translate(cx, 0));
      const rim = keep(outline.offset(grooveOffset + p.rimWidthMm, 'Round'));
      solids.push(keep(rim.extrude(T)));
      rims.push(rim);

      // V-groove built from thin slices: 45 degree walls, printable without supports.
      const n = Math.ceil(T / SLICE_MM);
      for (let i = 0; i < n; i++) {
        const z0 = i * SLICE_MM;
        const zMid = z0 + SLICE_MM / 2;
        const off = Math.min(grooveOffset, -p.frontLipMm + (T - zMid), -p.backLipMm + zMid);
        // Slices overlap a little: slices that only touch face to face leave internal membranes.
        const bottom = i === 0 ? -0.1 : z0 - 0.01;
        const top = i === n - 1 ? T + 0.1 : z0 + SLICE_MM + 0.01;
        const slice = keep(outline.offset(off, 'Round'));
        holes.push(keep(keep(slice.extrude(top - bottom)).translate(0, 0, bottom)));
      }
      const groove = keep(outline.offset(grooveOffset, 'Round'));
      grooveOutlines.push({ eye: lens.eye, pointsMm: groove.toPolygons()[0] ?? [] });
    }

    // Bridge and hinge lugs share a line in the upper part of the rims, as on most frames.
    const y = Math.max(right.bMm, left.bMm) * 0.15;
    // Horizontal extent of each rim along that line, so both parts are sure to overlap the rim.
    const [r, l] = rims.map((rim) => keep(rim.intersect(keep(CrossSection.square([1000, LUG.heightMm], true).translate(0, y)))).bounds());
    const overlap = 2;

    const bridgeLeft = r.max[0] - overlap;
    const bridgeRight = l.min[0] + overlap;
    solids.push(keep(Manifold.cube([bridgeRight - bridgeLeft, 6, T], true).translate((bridgeLeft + bridgeRight) / 2, y, T / 2)));

    // Hinge lugs on the temporal sides, sticking out of the back face, with a vertical pin hole.
    for (const x of [r.min[0] - LUG.widthMm / 2 + overlap, l.max[0] + LUG.widthMm / 2 - overlap]) {
      const height = T + LUG.depthMm;
      solids.push(keep(Manifold.cube([LUG.widthMm, LUG.heightMm, height], true).translate(x, y, T - height / 2)));
      const pin = keep(Manifold.cylinder(LUG.heightMm + 2, LUG.pinDiameterMm / 2, -1, 24, true));
      holes.push(keep(keep(pin.rotate([90, 0, 0])).translate(x, y, -LUG.depthMm / 2)));
    }

    const frame = keep(keep(Manifold.union(solids)).subtract(keep(Manifold.union(holes))));
    const parts = frame.decompose();
    parts.forEach(keep);
    if (parts.length !== 1) {
      throw new Error(`Frame has ${parts.length} disconnected parts`);
    }
    const printFrame = keep(keep(frame.rotate([0, 180, 0])).translate(0, 0, T));

    return {
      geometry: toGeometry(frame),
      printGeometry: toGeometry(printFrame),
      grooveOutlines,
      genus: frame.genus(),
      triangles: frame.numTri(),
      volumeMm3: frame.volume(),
    };
  } finally {
    for (const g of garbage) {
      g.delete();
    }
  }
}

function toGeometry(m: Manifold): BufferGeometry {
  const mesh = m.getMesh();
  const positions = new Float32Array(mesh.numVert * 3);
  for (let i = 0; i < mesh.numVert; i++) {
    for (let k = 0; k < 3; k++) {
      positions[i * 3 + k] = mesh.vertProperties[i * mesh.numProp + k];
    }
  }
  const indexed = new BufferGeometry();
  indexed.setAttribute('position', new BufferAttribute(positions, 3));
  indexed.setIndex(new BufferAttribute(mesh.triVerts, 1));
  // Flat shading: sharp edges stay sharp in the preview.
  const geometry = indexed.toNonIndexed();
  geometry.computeVertexNormals();
  indexed.dispose();
  return geometry;
}
