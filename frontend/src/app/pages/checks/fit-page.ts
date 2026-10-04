import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18n } from '../../core/i18n/i18n';
import { SessionStore } from '../../core/session.store';
import { FitCheck } from '../../fit-check/fit-check';
import { Icon } from '../../ui/icon';

/** Optional check: the measured contours over the generated rims. */
@Component({
  selector: 'app-fit-page',
  imports: [FitCheck, RouterLink, Icon],
  template: `
    <header class="step-head">
      <h2>{{ i18n.t('fit.title') }}</h2>
      <p class="lead">{{ i18n.t('fit.intro') }}</p>
    </header>
    @if (store.frame(); as f) {
      @if (store.lenses().R; as r) {
        @if (store.lenses().L; as l) {
          <app-fit-check [frame]="f" [right]="r.contour" [left]="l.contour" />
        }
      }
    } @else {
      <p class="note">
        <app-icon name="info" />
        <span>{{ i18n.t('files.needFrame') }}</span>
      </p>
      <a class="btn" routerLink="/monture">{{ i18n.t('files.goFrame') }}</a>
    }
  `,
})
export class FitPage {
  protected readonly i18n = inject(I18n);
  protected readonly store = inject(SessionStore);
}
