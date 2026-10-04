import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { FrameDesign } from '../../core/frame-design';
import { I18n } from '../../core/i18n/i18n';
import { SessionStore } from '../../core/session.store';
import { FacePreview } from '../../face-preview/face-preview';
import { Icon } from '../../ui/icon';

/** Optional check: the frame at true size on the face. Using the face's PD sends the user back to regenerate. */
@Component({
  selector: 'app-face-page',
  imports: [FacePreview, RouterLink, Icon],
  template: `
    <header class="step-head">
      <h2>{{ i18n.t('face.title') }}</h2>
      <p class="lead">{{ i18n.t('files.faceDesc') }}</p>
    </header>
    @if (store.frame(); as f) {
      <app-face-preview
        [outline]="f.frontOutline"
        [pdMm]="design.framePdMm()"
        (usePd)="usePd($event)"
      />
    } @else {
      <p class="note">
        <app-icon name="info" />
        <span>{{ i18n.t('files.needFrame') }}</span>
      </p>
      <a class="btn" routerLink="/monture">{{ i18n.t('files.goFrame') }}</a>
    }
  `,
})
export class FacePage {
  protected readonly i18n = inject(I18n);
  protected readonly store = inject(SessionStore);
  protected readonly design = inject(FrameDesign);
  private readonly router = inject(Router);

  protected usePd(pdMm: number): void {
    this.design.applyFacePd(pdMm);
    void this.router.navigate(['/monture']);
  }
}
