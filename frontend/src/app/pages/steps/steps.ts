import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MessageKey } from '../../core/i18n/fr';
import { I18n } from '../../core/i18n/i18n';
import { SessionStore } from '../../core/session.store';

/** Intermediate images of each measurement: markers, rectified sheet, contour. */
@Component({
  selector: 'app-steps',
  imports: [RouterLink],
  template: `
    <p>
      <a routerLink="/">{{ i18n.t('steps.back') }}</a>
    </p>
    @for (item of measured(); track item.eye) {
      <section class="card">
        <h2>{{ i18n.t(item.eye === 'R' ? 'lens.R' : 'lens.L') }}</h2>
        <p class="status">
          {{
            i18n.t('steps.details', {
              markers: item.r.markersFound,
              error: i18n.num(item.r.reprojectionErrorMm, '1.2-2'),
              ppm: i18n.num(item.r.pxPerMm, '1.0-2'),
              method: item.r.method,
              ms: item.r.elapsedMs,
            })
          }}
        </p>
        @for (step of item.r.steps; track step.label; let i = $index) {
          <h3>{{ stepLabel(i, step.label) }}</h3>
          <img [src]="step.imageDataUrl" [alt]="stepLabel(i, step.label)" />
        }
      </section>
    } @empty {
      <p class="status">{{ i18n.t('steps.none') }}</p>
    }
  `,
  styles: `
    img {
      width: 100%;
      border-radius: 8px;
    }
  `,
})
export class Steps {
  private readonly store = inject(SessionStore);
  protected readonly i18n = inject(I18n);
  protected readonly measured = computed(() =>
    (['R', 'L'] as const).flatMap((eye) => {
      const r = this.store.lenses()[eye]?.response;
      return r ? [{ eye, r }] : [];
    }),
  );

  /** The server names its 3 steps in French: translated by position, its label kept for any other step. */
  protected stepLabel(index: number, label: string): string {
    const key = `steps.${index + 1}`;
    return ['steps.1', 'steps.2', 'steps.3'].includes(key) ? this.i18n.t(key as MessageKey) : label;
  }
}
