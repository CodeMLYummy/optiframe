import { BufferGeometry, Mesh } from 'three';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';

import { LensContour } from './lens';

function contourBounds(lens: LensContour) {
  const xs = lens.pointsMm.map((p) => p[0]);
  const ys = lens.pointsMm.map((p) => p[1]);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function contourMarkup(
  lens: LensContour,
  offsetX: number,
  offsetY: number,
  labelX: number,
  labelY: number,
): string {
  // SVG y points down: flip without mirroring the front-facing outline.
  const d = lens.pointsMm
    .map(([x, y], i) => `${i ? 'L' : 'M'}${(x + offsetX).toFixed(3)} ${(offsetY - y).toFixed(3)}`)
    .join(' ');
  const label = `${lens.eye === 'R' ? 'OD (droit)' : 'OG (gauche)'}  A ${lens.aMm.toFixed(1)} mm  B ${lens.bMm.toFixed(1)} mm`;
  return `  <path d="${d} Z" fill="none" stroke="#000" stroke-width="0.2"/>
  <line x1="${(offsetX - 2).toFixed(3)}" y1="${offsetY.toFixed(3)}" x2="${(offsetX + 2).toFixed(3)}" y2="${offsetY.toFixed(3)}" stroke="#000" stroke-width="0.1"/>
  <line x1="${offsetX.toFixed(3)}" y1="${(offsetY - 2).toFixed(3)}" x2="${offsetX.toFixed(3)}" y2="${(offsetY + 2).toFixed(3)}" stroke="#000" stroke-width="0.1"/>
  <text x="${labelX.toFixed(3)}" y="${labelY.toFixed(3)}" font-size="3" font-family="sans-serif">${label}</text>`;
}

function svgDocument(width: number, height: number, content: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width.toFixed(3)}mm" height="${height.toFixed(3)}mm" viewBox="0 0 ${width.toFixed(3)} ${height.toFixed(3)}">
${content}
</svg>
`;
}

/** SVG at 1:1 scale: printed at 100%, the real lens must cover the outline exactly. */
export function contourSvg(lens: LensContour): string {
  const margin = 10;
  const bounds = contourBounds(lens);
  const w = bounds.maxX - bounds.minX + 2 * margin;
  const h = bounds.maxY - bounds.minY + 2 * margin;
  return svgDocument(
    w,
    h,
    contourMarkup(lens, margin - bounds.minX, bounds.maxY + margin, 2, h - 2),
  );
}

/** Both lenses viewed from the front (OD on the left), separated by a display gap, not a frame bridge. */
export function lensPairSvg(right: LensContour, left: LensContour): string {
  const margin = 10;
  const gap = 10;
  const r = contourBounds(right);
  const l = contourBounds(left);
  const rightWidth = r.maxX - r.minX;
  const leftX = margin + rightWidth + gap;
  const maxY = Math.max(r.maxY, l.maxY);
  const width = leftX + l.maxX - l.minX + margin;
  // Reserve two label rows so long measurement labels never overlap.
  const height = maxY - Math.min(r.minY, l.minY) + 2 * margin + 5;
  return svgDocument(
    width,
    height,
    [
      contourMarkup(right, margin - r.minX, margin + maxY, margin, height - 7),
      contourMarkup(left, leftX - l.minX, margin + maxY, margin, height - 2),
    ].join('\n'),
  );
}

export function stlBlob(geometry: BufferGeometry): Blob {
  const data = new STLExporter().parse(new Mesh(geometry), { binary: true }) as DataView;
  return new Blob([data.buffer as ArrayBuffer], { type: 'model/stl' });
}

export function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
