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

/** Rays around the lens centre used to sample the groove outlines: ~0.2 mm apart on a 50 mm lens. */
const GROOVE_RAYS = 720;
/** Mesh simplification tolerance: no surface moves by more than 1 um. */
const MESH_TOLERANCE_MM = 0.001;
const LUG = { widthMm: 4, heightMm: 8, depthMm: 6, pinDiameterMm: 1.6 };

/**
 * Temples (branches), a separate print: a fork whose two ears go above and below the lug, held by a pin through
 * the three holes (paper clip or 1.75 mm filament, tight in the lug, free in the ears). Straight, then bent down
 * behind the ear. Lengths are measured from the pin.
 */
export const TEMPLE = {
  lengthMm: 140,
  bendAtMm: 100,
  bendDeg: 25,
  heightMm: 5,
  thicknessMm: 3.5,
  /** Thickness of each ear of the fork. */
  earMm: 2.2,
  /** Gap around the lug, above, below and behind. */
  clearanceMm: 0.3,
  pinHoleMm: 1.9,
};

export interface FrameResult {
  /** Model coordinates, for the preview. */
  geometry: BufferGeometry;
  /** Same mesh rotated front face down on the bed, ready to print. */
  printGeometry: BufferGeometry;
  /** Front with both temples pinned and open, for the preview only. */
  previewGeometry: BufferGeometry;
  /** Both temples lying flat side by side, ready to print (separate file). */
  templesPrintGeometry: BufferGeometry;
  /**
   * Per lens, in the lens's own coordinates (same as its contour): the bottom of the groove and the opening of the
   * front lip, for the contour/frame coherence check.
   */
  fit: { eye: LensContour['eye']; grooveMm: Vec2[]; lipMm: Vec2[] }[];
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
  const { CrossSection, Manifold, Mesh } = await loadManifold();
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
    const fit: FrameResult['fit'] = [];
    const rims: CrossSection[] = [];

    for (const { lens, cx } of lenses) {
      const outline = keep(new CrossSection([lens.pointsMm as Vec2[]]).translate(cx, 0));
      rims.push(keep(outline.offset(grooveOffset + p.rimWidthMm, 'Round')));

      // V-groove: one solid cut with 45 degree walls (printable without supports), lofted between the outline
      // offsets at the profile's break points. A stack of thin slices left coincident walls that become
      // non-manifold edges once the STL's corners are welded.
      const cut = keep(new Manifold(new Mesh(grooveCut(outline, lens, cx, profile(p, grooveOffset)))));
      if (cut.status() !== 'NoError') {
        throw new Error(`Groove cut is not a valid solid: ${cut.status()}`);
      }
      holes.push(cut);
      const inLens = (c: CrossSection) => (c.toPolygons()[0] ?? []).map(([x, y]) => [x - cx, y] as Vec2);
      const lip = keep(outline.offset(-p.frontLipMm, 'Round'));
      fit.push({ eye: lens.eye, grooveMm: inLens(keep(outline.offset(grooveOffset, 'Round'))), lipMm: inLens(lip) });
    }

    // Bridge and hinge lugs share a line in the upper part of the rims, as on most frames.
    const y = Math.max(right.bMm, left.bMm) * 0.15;
    // Horizontal extent of each rim along that line, so both parts are sure to overlap the rim.
    const [r, l] = rims.map((rim) => keep(rim.intersect(keep(CrossSection.square([1000, LUG.heightMm], true).translate(0, y)))).bounds());
    const overlap = 2;

    const bridgeLeft = r.max[0] - overlap;
    const bridgeRight = l.min[0] + overlap;
    const bridge = keep(CrossSection.square([bridgeRight - bridgeLeft, 6], true).translate((bridgeLeft + bridgeRight) / 2, y));
    const lugXs = [r.min[0] - LUG.widthMm / 2 + overlap, l.max[0] + LUG.widthMm / 2 - overlap];
    const lugFootprints = lugXs.map((x) => keep(CrossSection.square([LUG.widthMm, LUG.heightMm], true).translate(x, y)));

    // Rims, bridge and the front of the hinge lugs are one 2D shape extruded once: separate solids flush with the
    // faces would share coplanar faces, which leave non-manifold edges once the STL's corners are welded.
    solids.push(keep(keep(CrossSection.union([...rims, bridge, ...lugFootprints])).extrude(T)));

    // Hinge lugs on the temporal sides, sticking out of the back face, with a vertical pin hole. The part behind
    // the frame overlaps 0.5 mm into it and is inset by 0.01 mm, so none of its faces coincide with the frame's.
    for (const x of lugXs) {
      const inset = 0.02;
      const depth = LUG.depthMm + 0.5;
      solids.push(keep(Manifold.cube([LUG.widthMm - inset, LUG.heightMm - inset, depth], true).translate(x, y, 0.5 - depth / 2)));
      const pin = keep(Manifold.cylinder(LUG.heightMm + 2, LUG.pinDiameterMm / 2, -1, 24, true));
      holes.push(keep(keep(pin.rotate([90, 0, 0])).translate(x, y, -LUG.depthMm / 2)));
    }

    // The booleans leave sliver triangles far below print resolution; written as float32 STL they collapse into
    // zero-area faces and edges shared by 4+ faces. Simplifying within 1 um removes them.
    const frame = keep(keep(keep(Manifold.union(solids)).subtract(keep(Manifold.union(holes)))).simplify(MESH_TOLERANCE_MM));
    const parts = frame.decompose();
    parts.forEach(keep);
    if (parts.length !== 1) {
      throw new Error(`Frame has ${parts.length} disconnected parts`);
    }
    const printFrame = keep(keep(frame.rotate([0, 180, 0])).translate(0, 0, T));

    // Temples: side profile (u behind the pin, v up) extruded through the thickness, then pinned to each lug.
    const temple = buildTemple(CrossSection, Manifold, keep);
    const pinZ = -LUG.depthMm / 2;
    const worn = lugXs.map((x) => keep(keep(temple.rotate([0, 90, 0])).translate(x - TEMPLE.thicknessMm / 2, y, pinZ)));
    const tb = temple.boundingBox();
    const pitch = tb.max[1] - tb.min[1] + 5;
    const templesPrint = keep(Manifold.union([temple, keep(temple.translate(0, pitch, 0))]));
    if (templesPrint.decompose().map(keep).length !== 2) {
      throw new Error('Temples overlap on the print bed');
    }
    if (worn.some((w) => keep(frame.intersect(w)).volume() > 0)) {
      throw new Error('Temple fork collides with the frame');
    }
    const preview = keep(Manifold.union([frame, ...worn]));

    return {
      geometry: toGeometry(frame),
      printGeometry: toGeometry(printFrame),
      previewGeometry: toGeometry(preview),
      templesPrintGeometry: toGeometry(templesPrint),
      fit,
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

/**
 * One temple in its side profile: x = u (mm behind the pin), y = v (up), z through the thickness (0 to
 * TEMPLE.thicknessMm), lying flat as printed. The fork clears the lug: the ears stop short of the frame's back face
 * whatever the angle, and the bridge of the fork stays outside the lug's turning circle.
 */
function buildTemple(
  CrossSection: ManifoldToplevel['CrossSection'],
  Manifold: ManifoldToplevel['Manifold'],
  keep: <T extends { delete(): void }>(x: T) => T,
): Manifold {
  const t = TEMPLE;
  const half = t.thicknessMm / 2;
  const gap = LUG.heightMm / 2 + t.clearanceMm;
  const top = gap + t.earMm;
  // Ears turn about the pin: their front corners must stay behind the frame's back face (pin is depth / 2 behind).
  const earFront = Math.sqrt((LUG.depthMm / 2 - t.clearanceMm) ** 2 - half ** 2);
  // Fork bridge: beyond the lug's farthest corner from the pin.
  const bridge0 = Math.hypot(LUG.widthMm / 2, LUG.depthMm / 2) + t.clearanceMm;
  const bridge1 = bridge0 + 3;
  const rect = (u0: number, u1: number, v0: number, v1: number) =>
    keep(CrossSection.square([u1 - u0, v1 - v0]).translate(u0, v0));
  const h = t.heightMm / 2;
  const bend = (t.bendDeg * Math.PI) / 180;
  const rest = t.lengthMm - t.bendAtMm;
  const tip: Vec2 = [t.bendAtMm + rest * Math.cos(bend), -rest * Math.sin(bend)];
  const disc = (c: Vec2) => keep(keep(CrossSection.circle(h, 32)).translate(c));
  const profile = keep(
    CrossSection.union([
      rect(-earFront, bridge1, gap, top),
      rect(-earFront, bridge1, -top, -gap),
      keep(CrossSection.hull([rect(bridge0, bridge1, -top, top), rect(bridge1 + 12, bridge1 + 13, -h, h)])),
      rect(bridge0, t.bendAtMm, -h, h),
      keep(CrossSection.hull([disc([t.bendAtMm, 0]), disc(tip)])),
    ]),
  );
  const body = keep(profile.extrude(t.thicknessMm));
  const pin = keep(keep(keep(Manifold.cylinder(2 * top + 2, t.pinHoleMm / 2, -1, 24, true)).rotate([90, 0, 0])).translate(0, 0, half));
  return keep(body.subtract(pin));
}

/**
 * Offset of the cut from the lens outline through the thickness, as (z, offset) break points: 45 degrees from the
 * back lip to the groove depth, flat, then 45 degrees to the front lip. The 45 degree walls continue 0.1 mm beyond
 * both faces, so no ring of the cut lies on a face of the rim (coplanar points leave non-manifold edges).
 */
function profile(p: FrameParams, grooveOffset: number): [number, number][] {
  const T = p.thicknessMm;
  const at = (z: number) => Math.min(grooveOffset, -p.frontLipMm + (T - z), -p.backLipMm + z);
  const rise = grooveOffset + p.backLipMm;
  const fall = T - p.frontLipMm - grooveOffset;
  // A thin frame never reaches the full groove depth: the two 45 degree walls meet.
  const peaks = rise <= fall ? [rise, fall] : [(T + p.backLipMm - p.frontLipMm) / 2];
  return [-0.1, ...peaks, T + 0.1].map((z) => [z, at(z)] as [number, number]);
}

/**
 * Closed triangle mesh of the groove cut. Each break point of the profile gives the lens outline offset by that
 * amount, sampled on the same rays from the lens centre (lenses are star-shaped around it), so consecutive rings
 * pair up point by point; rings are joined by triangle strips and closed by a fan at each end.
 */
function grooveCut(
  outline: CrossSection,
  lens: LensContour,
  cx: number,
  levels: [number, number][],
): { numProp: number; vertProperties: Float32Array; triVerts: Uint32Array } {
  const n = GROOVE_RAYS;
  const pts = lens.pointsMm;
  const centre: Vec2 = [cx + pts.reduce((s, q) => s + q[0], 0) / pts.length, pts.reduce((s, q) => s + q[1], 0) / pts.length];
  const verts: number[] = [];
  for (const [z, off] of levels) {
    const offset = outline.offset(off, 'Round');
    const polys = offset.toPolygons();
    offset.delete();
    const ring = polys.reduce((a, b) => (Math.abs(area(b)) > Math.abs(area(a)) ? b : a));
    for (let i = 0; i < n; i++) {
      const t = (2 * Math.PI * i) / n;
      const r = rayDistance(ring, centre, [Math.cos(t), Math.sin(t)]);
      verts.push(centre[0] + r * Math.cos(t), centre[1] + r * Math.sin(t), z);
    }
  }
  const k = levels.length;
  const bottom = k * n;
  const top = bottom + 1;
  verts.push(centre[0], centre[1], levels[0][0], centre[0], centre[1], levels[k - 1][0]);
  const tris: number[] = [];
  for (let l = 0; l < k - 1; l++) {
    for (let i = 0; i < n; i++) {
      const a = l * n + i;
      const b = l * n + ((i + 1) % n);
      const c = (l + 1) * n + ((i + 1) % n);
      const d = (l + 1) * n + i;
      tris.push(a, b, c, a, c, d); // CCW rings, z going up: normals point outward
    }
  }
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    tris.push(bottom, j, i); // facing -z
    tris.push(top, (k - 1) * n + i, (k - 1) * n + j); // facing +z
  }
  return { numProp: 3, vertProperties: new Float32Array(verts), triVerts: new Uint32Array(tris) };
}

function area(poly: Vec2[]): number {
  let s = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    s += x1 * y2 - x2 * y1;
  }
  return s / 2;
}

/** Distance from `origin` along the unit vector `dir` to the farthest crossing of the closed polygon. */
function rayDistance(poly: Vec2[], origin: Vec2, dir: Vec2): number {
  let best = 0;
  for (let i = 0; i < poly.length; i++) {
    const [ax, ay] = poly[i];
    const [bx, by] = poly[(i + 1) % poly.length];
    const ex = bx - ax;
    const ey = by - ay;
    const den = dir[0] * ey - dir[1] * ex;
    if (Math.abs(den) < 1e-12) {
      continue;
    }
    const wx = ax - origin[0];
    const wy = ay - origin[1];
    const t = (wx * ey - wy * ex) / den;
    const u = (wx * dir[1] - wy * dir[0]) / den;
    if (t > 0 && u >= 0 && u <= 1) {
      best = Math.max(best, t);
    }
  }
  return best;
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
