import { Injectable, computed, signal } from '@angular/core';

import { Eye, LensContour, MeasureResponse } from './lens';

export interface LensSlot {
  contour: LensContour;
  /** Missing for the test ellipses. */
  response?: MeasureResponse;
}

export interface PdInput {
  perEye: boolean;
  totalMm: number | null;
  rightMm: number | null;
  leftMm: number | null;
}

/** Results of the current session, shared by the pages. */
@Injectable({ providedIn: 'root' })
export class SessionStore {
  readonly lenses = signal<Partial<Record<Eye, LensSlot>>>({});
  readonly pd = signal<PdInput>({ perEye: false, totalMm: null, rightMm: null, leftMm: null });
  readonly bothMeasured = computed(() => !!this.lenses().L && !!this.lenses().R);
  /** Every photo measured for each lens in this session, oldest first, for the coherence between takes. */
  readonly takes = signal<Record<Eye, LensContour[]>>({ L: [], R: [] });

  set(eye: Eye, slot: LensSlot): void {
    this.lenses.update((l) => ({ ...l, [eye]: slot }));
    if (slot.response) {
      this.takes.update((t) => ({ ...t, [eye]: [...t[eye], slot.contour] }));
    }
  }

  clearTakes(eye: Eye): void {
    this.takes.update((t) => ({ ...t, [eye]: [] }));
  }
}
