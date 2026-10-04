import { Injectable, computed, effect, signal } from '@angular/core';

export type Paper = 'letter' | 'a4';

/** How the user describes the printed size: measured length of 10 squares, or the printer's scale. */
export type SizeMode = 'squares' | 'percent';

/** Nominal length of the 10 check squares printed on the sheet (10 x 15 mm). */
export const NOMINAL_TEN_SQUARES_MM = 150;

/** Same bounds as the server: outside, the sheet cannot be the OptiFrame sheet. */
export const MIN_PRINT_SCALE = 0.8;
export const MAX_PRINT_SCALE = 1.2;

export interface SheetInput {
  paper: Paper;
  mode: SizeMode;
  tenSquaresMm: number | null;
  percent: number | null;
}

export const DEFAULT_SHEET: SheetInput = { paper: 'letter', mode: 'squares', tenSquaresMm: 150, percent: 100 };

/** Printed size / nominal size, or null when the entered value is missing or implausible. */
export function printScale(input: SheetInput): number | null {
  const value = input.mode === 'squares' ? input.tenSquaresMm : input.percent;
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  const scale = input.mode === 'squares' ? value / NOMINAL_TEN_SQUARES_MM : value / 100;
  return scale >= MIN_PRINT_SCALE && scale <= MAX_PRINT_SCALE ? scale : null;
}

/** Printable reference sheet for the paper format, served from public/. */
export function sheetPdf(paper: Paper): string {
  return `feuille-charuco-${paper}.pdf`;
}

const STORAGE_KEY = 'optiframe.sheet';

/** Paper format and printed size of the reference sheet, remembered on this device. */
@Injectable({ providedIn: 'root' })
export class SheetSettings {
  readonly input = signal<SheetInput>(load());
  readonly scale = computed(() => printScale(this.input()));
  readonly pdf = computed(() => sheetPdf(this.input().paper));

  constructor() {
    effect(() => save(this.input()));
  }

  update(patch: Partial<SheetInput>): void {
    this.input.update((i) => ({ ...i, ...patch }));
  }
}

function load(): SheetInput {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const v = JSON.parse(raw) as Partial<SheetInput>;
      return {
        paper: v.paper === 'a4' ? 'a4' : 'letter',
        mode: v.mode === 'percent' ? 'percent' : 'squares',
        tenSquaresMm: typeof v.tenSquaresMm === 'number' ? v.tenSquaresMm : DEFAULT_SHEET.tenSquaresMm,
        percent: typeof v.percent === 'number' ? v.percent : DEFAULT_SHEET.percent,
      };
    }
  } catch {
    // Private mode or blocked storage: start from the defaults.
  }
  return { ...DEFAULT_SHEET };
}

function save(input: SheetInput): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(input));
  } catch {
    // Not saved: the settings still apply to this visit.
  }
}
