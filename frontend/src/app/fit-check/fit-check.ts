import { Component, computed, inject, input } from '@angular/core';

import { GapStats, gap } from '../core/coherence';
import { DEFAULT_FRAME, FrameResult } from '../core/frame-generator';
import { I18n } from '../core/i18n/i18n';
import { LensContour } from '../core/lens';

interface EyeFit {
  title: string;
  viewBox: string;
  paths: { contour: string; groove: string; lip: string };
  groove: GapStats;
  lip: GapStats;
}

/** Distance accepted around the designed gaps: the outlines are offset with rounded joins, sampled every ~0.2 mm. */
const FIT_TOLERANCE_MM = 0.1;

/**
 * Contour/frame coherence: the measured lens contour drawn over the frame's groove bottom and front lip opening,
 * with the gap between them measured all around the lens.
 */
@Component({
  selector: 'app-fit-check',
  template: `
    @for (f of fits(); track f.title) {
      <figure>
        <svg
          [attr.viewBox]="f.viewBox"
          role="img"
          [attr.aria-label]="i18n.t('fit.aria', { lens: f.title })"
        >
          <g transform="scale(1,-1)">
            <path class="lip" [attr.d]="f.paths.lip" />
            <path class="groove" [attr.d]="f.paths.groove" />
            <path class="contour" [attr.d]="f.paths.contour" />
          </g>
        </svg>
        <figcaption>
          <strong>{{ f.title }}</strong>
          <span
            [class.ok]="isOk(f.groove, expectedGroove)"
            [class.warn]="!isOk(f.groove, expectedGroove)"
          >
            {{ i18n.t('fit.groove', stats(f.groove, expectedGroove)) }}
          </span>
          <span [class.ok]="isOk(f.lip, expectedLip)" [class.warn]="!isOk(f.lip, expectedLip)">
            {{ i18n.t('fit.lip', stats(f.lip, expectedLip)) }}
          </span>
        </figcaption>
      </figure>
    }
    <p class="status legend">
      <span class="key contour"></span> {{ i18n.t('fit.keyContour') }}
      <span class="key groove"></span> {{ i18n.t('fit.keyGroove') }} <span class="key lip"></span>
      {{ i18n.t('fit.keyLip') }}
    </p>
  `,
  styles: `
    figure {
      margin: 0 0 12px;
    }
    svg {
      width: 100%;
      max-height: 220px;
      background: var(--surface-2);
      border-radius: 8px;
    }
    path {
      fill: none;
      vector-effect: non-scaling-stroke;
    }
    .contour {
      stroke: var(--text);
      stroke-width: 2;
    }
    .groove {
      stroke: var(--accent);
      stroke-width: 2;
      stroke-dasharray: 6 4;
    }
    .lip {
      stroke: var(--warn);
      stroke-width: 1.5;
    }
    figcaption {
      display: grid;
      gap: 2px;
      font-size: 0.9rem;
      margin-top: 4px;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 8px;
    }
    .key {
      display: inline-block;
      width: 18px;
      border-top: 2px solid;
    }
    .key.contour {
      border-color: var(--text);
    }
    .key.groove {
      border-color: var(--accent);
      border-top-style: dashed;
    }
    .key.lip {
      border-color: var(--warn);
    }
  `,
})
export class FitCheck {
  readonly frame = input.required<FrameResult>();
  readonly right = input.required<LensContour>();
  readonly left = input.required<LensContour>();

  protected readonly i18n = inject(I18n);

  protected readonly expectedGroove = DEFAULT_FRAME.clearanceMm + DEFAULT_FRAME.grooveDepthMm;
  protected readonly expectedLip = DEFAULT_FRAME.frontLipMm;

  protected readonly fits = computed<EyeFit[]>(() =>
    (['R', 'L'] as const).flatMap((eye) => {
      const lens = eye === 'R' ? this.right() : this.left();
      const f = this.frame().fit.find((x) => x.eye === eye);
      if (!f) {
        return [];
      }
      const xs = f.grooveMm.map((p) => p[0]);
      const ys = f.grooveMm.map((p) => p[1]);
      const m = 2;
      const [x0, x1, y0, y1] = [
        Math.min(...xs) - m,
        Math.max(...xs) + m,
        Math.min(...ys) - m,
        Math.max(...ys) + m,
      ];
      return [
        {
          title: this.i18n.t(eye === 'R' ? 'lens.R' : 'lens.L'),
          // The group flips y (contours are y up): the view box covers -y1..-y0.
          viewBox: `${x0} ${-y1} ${x1 - x0} ${y1 - y0}`,
          paths: { contour: path(lens.pointsMm), groove: path(f.grooveMm), lip: path(f.lipMm) },
          groove: gap(lens.pointsMm, f.grooveMm),
          // The lip is inside the lens: a negative gap, shown as how much of the lens edge it covers.
          lip: neg(gap(lens.pointsMm, f.lipMm)),
        },
      ];
    }),
  );

  protected stats(g: GapStats, expected: number): Record<string, string> {
    const n = (v: number) => this.i18n.num(v, '1.2-2');
    return {
      mean: n(g.meanMm),
      min: n(g.minMm),
      max: n(g.maxMm),
      expected: this.i18n.num(expected),
    };
  }

  protected isOk(g: GapStats, expected: number): boolean {
    return (
      Math.abs(g.minMm - expected) <= FIT_TOLERANCE_MM &&
      Math.abs(g.maxMm - expected) <= FIT_TOLERANCE_MM
    );
  }
}

function neg(g: GapStats): GapStats {
  return { minMm: -g.maxMm, meanMm: -g.meanMm, maxMm: -g.minMm };
}

function path(points: readonly (readonly [number, number])[]): string {
  return (
    points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ') + ' Z'
  );
}
