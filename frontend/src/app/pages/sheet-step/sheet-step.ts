import { Component, inject } from '@angular/core';

import { I18n } from '../../core/i18n/i18n';
import { NOMINAL_TEN_SQUARES_MM, Paper, SheetSettings, SizeMode } from '../../core/sheet-settings';
import { Icon } from '../../ui/icon';

/** Step 1: print the reference sheet and enter its real printed size. */
@Component({
  selector: 'app-sheet-step',
  imports: [Icon],
  template: `
    <header class="step-head">
      <h2>{{ i18n.t('sheet.title') }}</h2>
      <p class="lead">{{ i18n.t('sheet.lead') }}</p>
    </header>

    <section class="section">
      <h3><span class="ord">1</span>{{ i18n.t('sheet.print') }}</h3>
      <div class="seg" role="radiogroup" [attr.aria-label]="i18n.t('sheet.paper')">
        <label>
          <input
            type="radio"
            name="paper"
            [checked]="sheet.input().paper === 'letter'"
            (change)="setPaper('letter')"
          />
          {{ i18n.t('sheet.letter') }}
        </label>
        <label>
          <input
            type="radio"
            name="paper"
            [checked]="sheet.input().paper === 'a4'"
            (change)="setPaper('a4')"
          />
          {{ i18n.t('sheet.a4') }}
        </label>
      </div>
      <a class="btn block" [href]="sheet.pdf()" target="_blank" download>
        <app-icon name="download" />
        {{ i18n.t('sheet.download') }}
      </a>
    </section>

    <section class="section">
      <h3><span class="ord">2</span>{{ i18n.t('sheet.measure') }}</h3>
      <p class="muted small prose">{{ i18n.t('sheet.printHint', { mm: nominalTenSquaresMm }) }}</p>
      <div class="seg" role="radiogroup" [attr.aria-label]="i18n.t('sheet.sizeMode')">
        <label>
          <input
            type="radio"
            name="size-mode"
            [checked]="sheet.input().mode === 'squares'"
            (change)="setSizeMode('squares')"
          />
          {{ i18n.t('sheet.modeSquares') }}
        </label>
        <label>
          <input
            type="radio"
            name="size-mode"
            [checked]="sheet.input().mode === 'percent'"
            (change)="setSizeMode('percent')"
          />
          {{ i18n.t('sheet.modePercent') }}
        </label>
      </div>
      @if (sheet.input().mode === 'squares') {
        <label class="field">
          {{ i18n.t('sheet.squaresLabel') }}
          <span class="input">
            <input
              type="number"
              inputmode="decimal"
              min="120"
              max="180"
              step="0.1"
              placeholder="150"
              [attr.aria-invalid]="sheet.scale() === null"
              [value]="sheet.input().tenSquaresMm ?? ''"
              (input)="setSize($event)"
            />
            <span class="unit">mm</span>
          </span>
        </label>
      } @else {
        <label class="field">
          {{ i18n.t('sheet.percentLabel') }}
          <span class="input">
            <input
              type="number"
              inputmode="decimal"
              min="80"
              max="120"
              step="0.01"
              placeholder="100"
              [attr.aria-invalid]="sheet.scale() === null"
              [value]="sheet.input().percent ?? ''"
              (input)="setSize($event)"
            />
            <span class="unit">%</span>
          </span>
        </label>
      }
      @if (sheet.scale(); as s) {
        <p class="small muted num">
          {{ i18n.t('sheet.scaleUsed', { percent: i18n.num(s * 100, '1.2-2') }) }}
        </p>
      } @else {
        <p class="note error" role="alert">
          <app-icon name="alert" />
          <span>{{ i18n.t('sheet.invalid') }}</span>
        </p>
      }
    </section>

    <section class="section">
      <h3><span class="ord">3</span>{{ i18n.t('sheet.place') }}</h3>
      <p class="prose">
        {{ i18n.t('sheet.placement') }}
        <strong>{{ i18n.t('sheet.alignStrong') }}</strong
        >{{ i18n.t('sheet.alignRest') }}
      </p>
    </section>
  `,
})
export class SheetStep {
  protected readonly i18n = inject(I18n);
  protected readonly sheet = inject(SheetSettings);
  protected readonly nominalTenSquaresMm = NOMINAL_TEN_SQUARES_MM;

  protected setPaper(paper: Paper): void {
    this.sheet.update({ paper });
  }

  protected setSizeMode(mode: SizeMode): void {
    this.sheet.update({ mode });
  }

  protected setSize(event: Event): void {
    const value = (event.target as HTMLInputElement).valueAsNumber;
    const v = Number.isFinite(value) && value > 0 ? value : null;
    this.sheet.update(this.sheet.input().mode === 'squares' ? { tenSquaresMm: v } : { percent: v });
  }
}
