import { Component, computed, inject, input, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';

import { contourSvg, download } from '../core/exports';
import { Eye, ellipseContour } from '../core/lens';
import { MeasureService } from '../core/measure.service';
import { SessionStore } from '../core/session.store';
import { SheetSettings } from '../core/sheet-settings';

@Component({
  selector: 'app-lens-capture',
  imports: [DecimalPipe],
  templateUrl: './lens-capture.html',
  styleUrl: './lens-capture.css',
})
export class LensCapture {
  readonly eye = input.required<Eye>();

  private readonly api = inject(MeasureService);
  private readonly store = inject(SessionStore);
  private readonly sheet = inject(SheetSettings);

  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly slot = computed(() => this.store.lenses()[this.eye()]);
  protected readonly title = computed(() => (this.eye() === 'R' ? 'Verre droit (OD)' : 'Verre gauche (OG)'));
  protected readonly controlImage = computed(() => this.slot()?.response?.steps.at(-1)?.imageDataUrl);

  protected async onFile(event: Event): Promise<void> {
    const inputEl = event.target as HTMLInputElement;
    const file = inputEl.files?.[0];
    inputEl.value = '';
    if (!file) {
      return;
    }
    const scale = this.sheet.scale();
    if (scale === null) {
      this.error.set("Taille d'impression de la feuille invalide : vérifiez la longueur des 10 cases (en haut).");
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      const response = await this.api.measure(file, this.eye(), scale);
      this.store.set(this.eye(), { contour: response.contour, response });
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.busy.set(false);
    }
  }

  protected useTestLens(): void {
    this.error.set(null);
    this.store.set(this.eye(), { contour: ellipseContour(this.eye()) });
  }

  protected downloadSvg(): void {
    const slot = this.slot();
    if (slot) {
      download(new Blob([contourSvg(slot.contour)], { type: 'image/svg+xml' }), `contour-${this.eye()}.svg`);
    }
  }
}
