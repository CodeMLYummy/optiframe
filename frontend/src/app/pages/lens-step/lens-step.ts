import { Component, computed, inject, input } from '@angular/core';

import { I18n } from '../../core/i18n/i18n';
import { Eye } from '../../core/lens';
import { LensCapture } from '../../lens-capture/lens-capture';

/** Steps 2 and 3: one lens each, the eye given by the route. */
@Component({
  selector: 'app-lens-step',
  imports: [LensCapture],
  template: `
    <header class="step-head">
      <h2>
        {{ i18n.t(eye() === 'R' ? 'step.right' : 'step.left') }}
        <span class="plate">{{ plate() }}</span>
      </h2>
      <p class="lead">{{ i18n.t(eye() === 'R' ? 'lens.leadR' : 'lens.leadL') }}</p>
    </header>
    @switch (eye()) {
      @case ('R') {
        <app-lens-capture eye="R" />
      }
      @case ('L') {
        <app-lens-capture eye="L" />
      }
    }
  `,
})
export class LensStep {
  /** From the route data. */
  readonly eye = input.required<Eye>();
  protected readonly i18n = inject(I18n);
  /** OD / OG in French and Spanish, OD / OS in English: taken from the lens names. */
  protected readonly plate = computed(
    () => /\((\w+)\)/.exec(this.i18n.t(this.eye() === 'R' ? 'lens.R' : 'lens.L'))?.[1] ?? '',
  );
}
