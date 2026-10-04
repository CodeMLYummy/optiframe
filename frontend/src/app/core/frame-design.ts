import { Injectable, computed, inject, signal } from '@angular/core';

import { download, stlBlob } from './exports';
import { generateFrame } from './frame-generator';
import { MessageKey } from './i18n/fr';
import { I18n } from './i18n/i18n';
import {
  COMFORT_BRIDGE_MM,
  MIN_BRIDGE_MM,
  MonocularPd,
  bridgeFromPd,
  pdFromBridge,
  splitPd,
} from './pd';
import { PdInput, SessionStore } from './session.store';

/** PD, bridge and frame generation, shared by the Frame step, the Files step and the face preview. */
@Injectable({ providedIn: 'root' })
export class FrameDesign {
  private readonly store = inject(SessionStore);
  private readonly i18n = inject(I18n);

  readonly generating = signal(false);
  /** Kept as a key, so it follows a change of language. */
  private readonly errorKey = signal<MessageKey | null>(null);
  readonly error = computed(() => {
    const key = this.errorKey();
    return key ? this.i18n.t(key) : null;
  });

  /** Null when no PD was entered: the frame then uses the standard bridge. */
  private readonly enteredPd = computed<MonocularPd | null>(() => {
    const pd = this.store.pd();
    if (!pd.perEye) {
      return pd.totalMm ? splitPd(pd.totalMm) : null;
    }
    return pd.rightMm && pd.leftMm ? { rightMm: pd.rightMm, leftMm: pd.leftMm } : null;
  });

  readonly usesPd = computed(() => this.enteredPd() !== null);

  readonly placement = computed(() => {
    const { L, R } = this.store.lenses();
    if (!L || !R) {
      return null;
    }
    const pd = this.enteredPd() ?? pdFromBridge(R.contour, L.contour);
    return { pd, bridgeMm: bridgeFromPd(R.contour, L.contour, pd) };
  });

  readonly bridgeWarning = computed(() => {
    const b = this.placement()?.bridgeMm;
    if (b === undefined || !this.usesPd()) {
      return null;
    }
    if (b < MIN_BRIDGE_MM) {
      return this.i18n.t('frame.pdTooSmall', { mm: this.i18n.num(b), min: MIN_BRIDGE_MM });
    }
    if (b < COMFORT_BRIDGE_MM.min || b > COMFORT_BRIDGE_MM.max) {
      return this.i18n.t('frame.bridgeUnusual', {
        mm: this.i18n.num(b),
        min: COMFORT_BRIDGE_MM.min,
        max: COMFORT_BRIDGE_MM.max,
      });
    }
    return null;
  });

  readonly canGenerate = computed(
    () =>
      this.store.bothMeasured() &&
      !this.generating() &&
      (this.placement()?.bridgeMm ?? 0) >= MIN_BRIDGE_MM,
  );

  /** PD the generated frame uses, entered or from the standard bridge. */
  readonly framePdMm = computed(() => {
    const pd = this.placement()?.pd;
    return pd ? pd.rightMm + pd.leftMm : null;
  });

  setPd(patch: Partial<PdInput>): void {
    this.store.pd.update((pd) => ({ ...pd, ...patch }));
    this.store.frame.set(null);
  }

  /** PD estimated on the face: replaces the entered one; the frame has to be generated again. */
  applyFacePd(pdMm: number): void {
    this.store.pd.set({
      perEye: false,
      totalMm: Math.round(pdMm * 2) / 2,
      rightMm: null,
      leftMm: null,
    });
    this.store.frame.set(null);
  }

  downloadStl(): void {
    const f = this.store.frame();
    if (f) {
      download(stlBlob(f.printGeometry), 'monture.stl');
    }
  }

  async generate(): Promise<void> {
    const { L, R } = this.store.lenses();
    const placement = this.placement();
    if (!L || !R || !placement) {
      return;
    }
    this.generating.set(true);
    this.errorKey.set(null);
    try {
      this.store.frame.set(await generateFrame(R.contour, L.contour, placement.pd));
    } catch (e) {
      console.error(e);
      this.errorKey.set('frame.failed');
    } finally {
      this.generating.set(false);
    }
  }
}
