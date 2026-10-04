import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { download, lensPairSvg, stlBlob } from '../../core/exports';
import { FrameDesign } from '../../core/frame-design';
import { TEMPLE } from '../../core/frame-generator';
import { I18n } from '../../core/i18n/i18n';
import { SessionStore } from '../../core/session.store';
import { Icon } from '../../ui/icon';

/** Step 5: the files to print, then the optional checks. */
@Component({
  selector: 'app-files-step',
  imports: [RouterLink, Icon],
  template: `
    <header class="step-head">
      <h2>{{ i18n.t('step.files') }}</h2>
      <p class="lead">{{ i18n.t('files.lead') }}</p>
    </header>

    <section class="section">
      <h3>{{ i18n.t('files.print3d') }}</h3>
      @if (store.frame(); as f) {
        <div class="rows">
          <button class="row" type="button" (click)="design.downloadStl()">
            <app-icon name="box" />
            <span>
              <span class="title">{{ i18n.t('frame.downloadFront') }}</span>
              <span class="desc num">{{
                i18n.t('files.frontDesc', { cm3: i18n.num(f.volumeMm3 / 1000) })
              }}</span>
            </span>
            <app-icon name="download" class="end" />
          </button>
          <button class="row" type="button" (click)="downloadTemplesStl()">
            <app-icon name="glasses" />
            <span>
              <span class="title">{{ i18n.t('frame.downloadTemples') }}</span>
              <span class="desc">{{ i18n.t('files.templesDesc', { mm: templeLengthMm }) }}</span>
            </span>
            <app-icon name="download" class="end" />
          </button>
        </div>
        <p class="small muted prose">{{ i18n.t('frame.templesHint') }}</p>
      } @else {
        <p class="note">
          <app-icon name="info" />
          <span>{{ i18n.t('files.needFrame') }}</span>
        </p>
        <a class="btn" routerLink="/monture">{{ i18n.t('files.goFrame') }}</a>
      }
    </section>

    <section class="section">
      <h3>{{ i18n.t('files.paper') }}</h3>
      <div class="rows">
        <button
          class="row"
          type="button"
          [disabled]="!store.bothMeasured()"
          (click)="downloadLensPairSvg()"
        >
          <app-icon name="file-text" />
          <span>
            <span class="title">{{ i18n.t('pair.download') }}</span>
            <span class="desc">{{ i18n.t('files.pairDesc') }}</span>
          </span>
          <app-icon name="download" class="end" />
        </button>
      </div>
      <p class="small muted prose">
        {{ i18n.t(store.bothMeasured() ? 'pair.hint' : 'pair.measureBoth') }}
      </p>
    </section>

    <section class="section">
      <h3>{{ i18n.t('files.checks') }}</h3>
      <nav class="rows">
        @if (store.frame()) {
          <a class="row" routerLink="/verification">
            <app-icon name="scan-line" />
            <span>
              <span class="title">{{ i18n.t('fit.title') }}</span>
              <span class="desc">{{ i18n.t('files.fitDesc') }}</span>
            </span>
            <app-icon name="chevron-right" class="end" />
          </a>
          <a class="row" routerLink="/essayage">
            <app-icon name="scan-face" />
            <span>
              <span class="title">{{ i18n.t('face.title') }}</span>
              <span class="desc">{{ i18n.t('files.faceDesc') }}</span>
            </span>
            <app-icon name="chevron-right" class="end" />
          </a>
        }
        <a class="row" routerLink="/pas-a-pas">
          <app-icon name="layers" />
          <span>
            <span class="title">{{ i18n.t('steps.title') }}</span>
            <span class="desc">{{ i18n.t('files.stepsDesc') }}</span>
          </span>
          <app-icon name="chevron-right" class="end" />
        </a>
      </nav>
    </section>
  `,
})
export class FilesStep {
  protected readonly i18n = inject(I18n);
  protected readonly store = inject(SessionStore);
  protected readonly design = inject(FrameDesign);
  protected readonly templeLengthMm = TEMPLE.lengthMm;

  protected downloadTemplesStl(): void {
    const f = this.store.frame();
    if (f) {
      download(stlBlob(f.templesPrintGeometry), 'branches.stl');
    }
  }

  protected downloadLensPairSvg(): void {
    const { L, R } = this.store.lenses();
    if (L && R) {
      download(
        new Blob([lensPairSvg(R.contour, L.contour)], { type: 'image/svg+xml' }),
        'contours-paire.svg',
      );
    }
  }
}
