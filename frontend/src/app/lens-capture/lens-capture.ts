import { Component, computed, inject, input, signal } from '@angular/core';

import { JURY_TOLERANCE_MM, spread } from '../core/coherence';
import { AppError, I18n } from '../core/i18n/i18n';
import { Eye, ellipseContour } from '../core/lens';
import { MeasureService } from '../core/measure.service';
import { SessionStore } from '../core/session.store';
import { SheetSettings } from '../core/sheet-settings';

@Component({
  selector: 'app-lens-capture',
  imports: [],
  templateUrl: './lens-capture.html',
  styleUrl: './lens-capture.css',
})
export class LensCapture {
  readonly eye = input.required<Eye>();

  private readonly api = inject(MeasureService);
  private readonly store = inject(SessionStore);
  private readonly sheet = inject(SheetSettings);
  protected readonly i18n = inject(I18n);

  protected readonly busy = signal(false);
  /** Kept untranslated, so it follows a change of language. */
  private readonly failure = signal<unknown>(null);
  protected readonly error = computed(() => (this.failure() ? this.i18n.error(this.failure()) : null));
  protected readonly slot = computed(() => this.store.lenses()[this.eye()]);
  protected readonly title = computed(() => this.i18n.t(this.eye() === 'R' ? 'lens.R' : 'lens.L'));
  protected readonly controlImage = computed(() => this.slot()?.response?.steps.at(-1)?.imageDataUrl);
  protected readonly takes = computed(() => this.store.takes()[this.eye()]);
  /** Spread of A and B between the photos of this lens, once there are at least two. */
  protected readonly spread = computed(() => (this.takes().length >= 2 ? spread(this.takes()) : null));
  protected readonly tolerance = JURY_TOLERANCE_MM;

  protected clearTakes(): void {
    this.store.clearTakes(this.eye());
  }

  protected async onFile(event: Event): Promise<void> {
    const inputEl = event.target as HTMLInputElement;
    const file = inputEl.files?.[0];
    inputEl.value = '';
    if (!file) {
      return;
    }
    const scale = this.sheet.scale();
    if (scale === null) {
      this.failure.set(new AppError('lens.badScale'));
      return;
    }
    this.busy.set(true);
    this.failure.set(null);
    try {
      const response = await this.api.measure(file, this.eye(), scale);
      this.store.set(this.eye(), { contour: response.contour, response });
    } catch (e) {
      this.failure.set(e);
    } finally {
      this.busy.set(false);
    }
  }

  protected useTestLens(): void {
    this.failure.set(null);
    this.store.set(this.eye(), { contour: ellipseContour(this.eye()) });
  }
}
