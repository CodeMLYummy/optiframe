import { Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { download, lensPairSvg, stlBlob } from '../../core/exports';
import { FrameResult, TEMPLE, generateFrame } from '../../core/frame-generator';
import {
  COMFORT_BRIDGE_MM,
  DEFAULT_BRIDGE_MM,
  MIN_BRIDGE_MM,
  MonocularPd,
  bridgeFromPd,
  pdFromBridge,
  splitPd,
} from '../../core/pd';
import { PdInput, SessionStore } from '../../core/session.store';
import { NOMINAL_TEN_SQUARES_MM, Paper, SheetSettings, SizeMode } from '../../core/sheet-settings';
import { FitCheck } from '../../fit-check/fit-check';
import { FrameViewer } from '../../frame-viewer/frame-viewer';
import { LensCapture } from '../../lens-capture/lens-capture';

@Component({
  selector: 'app-home',
  imports: [DecimalPipe, RouterLink, LensCapture, FrameViewer, FitCheck],
  templateUrl: './home.html',
})
export class Home {
  protected readonly store = inject(SessionStore);
  protected readonly sheet = inject(SheetSettings);
  protected readonly nominalTenSquaresMm = NOMINAL_TEN_SQUARES_MM;
  protected readonly frame = signal<FrameResult | null>(null);
  protected readonly generating = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly hasSteps = computed(() => Object.values(this.store.lenses()).some((s) => s?.response));
  protected readonly defaultBridgeMm = DEFAULT_BRIDGE_MM;

  /** Null when no PD was entered: the frame then uses the standard bridge. */
  private readonly enteredPd = computed<MonocularPd | null>(() => {
    const pd = this.store.pd();
    if (!pd.perEye) {
      return pd.totalMm ? splitPd(pd.totalMm) : null;
    }
    return pd.rightMm && pd.leftMm ? { rightMm: pd.rightMm, leftMm: pd.leftMm } : null;
  });

  protected readonly usesPd = computed(() => this.enteredPd() !== null);

  protected readonly placement = computed(() => {
    const { L, R } = this.store.lenses();
    if (!L || !R) {
      return null;
    }
    const pd = this.enteredPd() ?? pdFromBridge(R.contour, L.contour);
    return { pd, bridgeMm: bridgeFromPd(R.contour, L.contour, pd) };
  });

  protected readonly bridgeWarning = computed(() => {
    const b = this.placement()?.bridgeMm;
    if (b === undefined || !this.usesPd()) {
      return null;
    }
    if (b < MIN_BRIDGE_MM) {
      return `PD trop petit pour ces verres : il ne reste que ${b.toFixed(1)} mm pour le pont (minimum ${MIN_BRIDGE_MM} mm).`;
    }
    if (b < COMFORT_BRIDGE_MM.min || b > COMFORT_BRIDGE_MM.max) {
      return `Pont de ${b.toFixed(1)} mm, hors de la plage habituelle (${COMFORT_BRIDGE_MM.min} à ${COMFORT_BRIDGE_MM.max} mm). Vérifiez le PD et la taille des verres.`;
    }
    return null;
  });

  protected readonly canGenerate = computed(
    () => this.store.bothMeasured() && !this.generating() && (this.placement()?.bridgeMm ?? 0) >= MIN_BRIDGE_MM,
  );

  protected setPaper(event: Event): void {
    this.sheet.update({ paper: (event.target as HTMLSelectElement).value as Paper });
  }

  protected setSizeMode(mode: SizeMode): void {
    this.sheet.update({ mode });
  }

  protected setSize(event: Event): void {
    const value = (event.target as HTMLInputElement).valueAsNumber;
    const v = Number.isFinite(value) && value > 0 ? value : null;
    this.sheet.update(this.sheet.input().mode === 'squares' ? { tenSquaresMm: v } : { percent: v });
  }

  protected setPd(field: keyof Omit<PdInput, 'perEye'>, event: Event): void {
    const value = (event.target as HTMLInputElement).valueAsNumber;
    this.store.pd.update((pd) => ({ ...pd, [field]: Number.isFinite(value) && value > 0 ? value : null }));
    this.frame.set(null);
  }

  protected setPerEye(event: Event): void {
    const perEye = (event.target as HTMLInputElement).checked;
    this.store.pd.update((pd) => ({ ...pd, perEye }));
    this.frame.set(null);
  }

  protected async generate(): Promise<void> {
    const { L, R } = this.store.lenses();
    const placement = this.placement();
    if (!L || !R || !placement) {
      return;
    }
    this.generating.set(true);
    this.error.set(null);
    try {
      this.frame.set(await generateFrame(R.contour, L.contour, placement.pd));
    } catch (e) {
      console.error(e);
      this.error.set('Impossible de générer la monture avec ces contours. Reprenez les photos.');
    } finally {
      this.generating.set(false);
    }
  }

  protected downloadStl(): void {
    const f = this.frame();
    if (f) {
      download(stlBlob(f.printGeometry), 'monture.stl');
    }
  }

  protected downloadLensPairSvg(): void {
    const { L, R } = this.store.lenses();
    if (!L || !R) {
      this.error.set("Mesurez les deux verres avant d'exporter leurs contours.");
      return;
    }
    download(new Blob([lensPairSvg(R.contour, L.contour)], { type: 'image/svg+xml' }), 'contours-paire.svg');
  }

  protected readonly templeLengthMm = TEMPLE.lengthMm;

  protected downloadTemplesStl(): void {
    const f = this.frame();
    if (f) {
      download(stlBlob(f.templesPrintGeometry), 'branches.stl');
    }
  }
}
