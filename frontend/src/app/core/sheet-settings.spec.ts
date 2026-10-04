import { DEFAULT_SHEET, printScale, sheetPdf } from './sheet-settings';

describe('reference sheet settings', () => {
  it('turns the measured length of 10 squares into a print scale', () => {
    expect(printScale({ ...DEFAULT_SHEET, mode: 'squares', tenSquaresMm: 146.8 })).toBeCloseTo(0.9787, 4);
  });

  it('turns a printer percentage into a print scale', () => {
    expect(printScale({ ...DEFAULT_SHEET, mode: 'percent', percent: 97.87 })).toBeCloseTo(0.9787, 4);
  });

  it('is 1 for a sheet printed at true size', () => {
    expect(printScale(DEFAULT_SHEET)).toBe(1);
  });

  it('rejects missing or implausible values', () => {
    expect(printScale({ ...DEFAULT_SHEET, tenSquaresMm: null })).toBeNull();
    expect(printScale({ ...DEFAULT_SHEET, tenSquaresMm: 75 })).toBeNull(); // 5 squares measured instead of 10
    expect(printScale({ ...DEFAULT_SHEET, mode: 'percent', percent: 200 })).toBeNull();
  });

  it('serves the PDF of the chosen paper format', () => {
    expect(sheetPdf('letter')).toBe('feuille-charuco-letter.pdf');
    expect(sheetPdf('a4')).toBe('feuille-charuco-a4.pdf');
  });
});
