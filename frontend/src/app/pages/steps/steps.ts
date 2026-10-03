import { Component, computed, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { SessionStore } from '../../core/session.store';

/** Intermediate images of each measurement: markers, rectified sheet, contour. */
@Component({
  selector: 'app-steps',
  imports: [DecimalPipe, RouterLink],
  template: `
    <p><a routerLink="/">← Retour</a></p>
    @for (item of measured(); track item.eye) {
      <section class="card">
        <h2>{{ item.eye === 'R' ? 'Verre droit (OD)' : 'Verre gauche (OG)' }}</h2>
        <p class="status">
          {{ item.r.markersFound }} marqueurs · écart d'ajustement {{ item.r.reprojectionErrorMm | number: '1.2-2' }} mm ·
          {{ item.r.pxPerMm }} px/mm · {{ item.r.method }} · {{ item.r.elapsedMs }} ms
        </p>
        @for (step of item.r.steps; track step.label) {
          <h3>{{ step.label }}</h3>
          <img [src]="step.imageDataUrl" [alt]="step.label" />
        }
      </section>
    } @empty {
      <p class="status">Aucune photo mesurée pour l'instant.</p>
    }
  `,
  styles: `img { width: 100%; border-radius: 8px; }`,
})
export class Steps {
  private readonly store = inject(SessionStore);
  protected readonly measured = computed(() =>
    (['R', 'L'] as const).flatMap((eye) => {
      const r = this.store.lenses()[eye]?.response;
      return r ? [{ eye, r }] : [];
    }),
  );
}
