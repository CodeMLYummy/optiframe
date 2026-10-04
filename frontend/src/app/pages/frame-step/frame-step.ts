import { Component, inject } from '@angular/core';

import { DEFAULT_BRIDGE_MM } from '../../core/pd';
import { FrameDesign } from '../../core/frame-design';
import { I18n } from '../../core/i18n/i18n';
import { PdInput, SessionStore } from '../../core/session.store';
import { FrameViewer } from '../../frame-viewer/frame-viewer';
import { Icon } from '../../ui/icon';

/** Step 4: the patient's PD, the resulting bridge, and the generated frame. Generating is the bar's main action. */
@Component({
  selector: 'app-frame-step',
  imports: [FrameViewer, Icon],
  template: `
    <header class="step-head">
      <h2>{{ i18n.t('frame.title') }}</h2>
      <p class="lead">{{ i18n.t('frame.lead') }}</p>
    </header>

    @if (!store.bothMeasured()) {
      <p class="note warn" role="status">
        <app-icon name="alert" />
        <span>{{ i18n.t('frame.measureFirst') }}</span>
      </p>
    }

    <section class="section">
      @if (!store.pd().perEye) {
        <label class="field">
          {{ i18n.t('frame.pd') }}
          <span class="input">
            <input
              type="number"
              inputmode="decimal"
              min="40"
              max="80"
              step="0.5"
              [placeholder]="i18n.t('frame.pdExample')"
              [value]="store.pd().totalMm ?? ''"
              (input)="setPd('totalMm', $event)"
            />
            <span class="unit">mm</span>
          </span>
        </label>
      } @else {
        <div class="pair">
          <label class="field">
            {{ i18n.t('frame.pdRight') }}
            <span class="input">
              <input
                type="number"
                inputmode="decimal"
                min="20"
                max="40"
                step="0.5"
                [placeholder]="i18n.t('frame.pdHalfExample')"
                [value]="store.pd().rightMm ?? ''"
                (input)="setPd('rightMm', $event)"
              />
              <span class="unit">mm</span>
            </span>
          </label>
          <label class="field">
            {{ i18n.t('frame.pdLeft') }}
            <span class="input">
              <input
                type="number"
                inputmode="decimal"
                min="20"
                max="40"
                step="0.5"
                [placeholder]="i18n.t('frame.pdHalfExample')"
                [value]="store.pd().leftMm ?? ''"
                (input)="setPd('leftMm', $event)"
              />
              <span class="unit">mm</span>
            </span>
          </label>
        </div>
      }
      <label class="check">
        <input type="checkbox" [checked]="store.pd().perEye" (change)="setPerEye($event)" />
        {{ i18n.t('frame.perEye') }}
      </label>

      @if (design.placement(); as p) {
        <p class="bridge">
          @if (design.usesPd()) {
            <span class="muted">{{ i18n.t('frame.bridge') }}</span>
            <strong class="num">{{ i18n.num(p.bridgeMm) }} mm</strong>
          } @else {
            <span class="muted">{{ i18n.t('frame.standardBridge', { mm: defaultBridgeMm }) }}</span>
          }
        </p>
      }
      @if (design.bridgeWarning(); as warning) {
        <p class="note warn" role="alert">
          <app-icon name="alert" />
          <span>{{ warning }}</span>
        </p>
      }
      @if (design.error(); as message) {
        <p class="note error" role="alert">
          <app-icon name="alert" />
          <span>{{ message }}</span>
        </p>
      }
    </section>

    @if (store.frame(); as f) {
      <section class="section">
        <h3>
          <app-icon name="circle-check" class="ok" />
          {{ i18n.t('frame.ready') }}
        </h3>
        <figure class="reg">
          <app-frame-viewer class="media" [geometry]="f.previewGeometry" />
          <figcaption class="num">
            {{ i18n.t('frame.viewerHint') }}
            {{
              i18n.t('frame.stats', { triangles: f.triangles, cm3: i18n.num(f.volumeMm3 / 1000) })
            }}
          </figcaption>
        </figure>
      </section>
    }
  `,
  styles: `
    .bridge {
      display: flex;
      align-items: baseline;
      gap: 10px;
    }
    .bridge strong {
      font-size: 1.3rem;
      font-stretch: 125%;
    }
    h3 app-icon {
      align-self: center;
    }
  `,
})
export class FrameStep {
  protected readonly i18n = inject(I18n);
  protected readonly store = inject(SessionStore);
  protected readonly design = inject(FrameDesign);
  protected readonly defaultBridgeMm = DEFAULT_BRIDGE_MM;

  protected setPd(field: keyof Omit<PdInput, 'perEye'>, event: Event): void {
    const value = (event.target as HTMLInputElement).valueAsNumber;
    this.design.setPd({ [field]: Number.isFinite(value) && value > 0 ? value : null });
  }

  protected setPerEye(event: Event): void {
    this.design.setPd({ perEye: (event.target as HTMLInputElement).checked });
  }
}
