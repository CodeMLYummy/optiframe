import { BufferGeometry, Mesh } from 'three';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';

import { LensContour } from './lens';

/** SVG at 1:1 scale: printed at 100%, the real lens must cover the outline exactly. */
export function contourSvg(lens: LensContour): string {
  const margin = 10;
  const xs = lens.pointsMm.map((p) => p[0]);
  const ys = lens.pointsMm.map((p) => p[1]);
  const minX = Math.min(...xs) - margin;
  const maxY = Math.max(...ys) + margin;
  const w = Math.max(...xs) + margin - minX;
  const h = maxY - (Math.min(...ys) - margin);
  // SVG y points down: flip.
  const d = lens.pointsMm.map(([x, y], i) => `${i ? 'L' : 'M'}${(x - minX).toFixed(3)} ${(maxY - y).toFixed(3)}`).join(' ');
  const label = `${lens.eye === 'R' ? 'OD (droit)' : 'OG (gauche)'}  A ${lens.aMm.toFixed(1)} mm  B ${lens.bMm.toFixed(1)} mm`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${w.toFixed(3)}mm" height="${h.toFixed(3)}mm" viewBox="0 0 ${w.toFixed(3)} ${h.toFixed(3)}">
  <path d="${d} Z" fill="none" stroke="#000" stroke-width="0.2"/>
  <line x1="${(-minX - 2).toFixed(3)}" y1="${maxY.toFixed(3)}" x2="${(-minX + 2).toFixed(3)}" y2="${maxY.toFixed(3)}" stroke="#000" stroke-width="0.1"/>
  <line x1="${(-minX).toFixed(3)}" y1="${(maxY - 2).toFixed(3)}" x2="${(-minX).toFixed(3)}" y2="${(maxY + 2).toFixed(3)}" stroke="#000" stroke-width="0.1"/>
  <text x="2" y="${(h - 2).toFixed(3)}" font-size="3" font-family="sans-serif">${label}</text>
</svg>
`;
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
