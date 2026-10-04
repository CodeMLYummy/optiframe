import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';

import { lensPairSvg } from '../../core/exports';
import { I18n } from '../../core/i18n/i18n';
import { ellipseContour } from '../../core/lens';
import { SessionStore } from '../../core/session.store';
import { Home } from './home';

describe('Home lens pair export', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideHttpClient(), provideRouter([])],
    }).compileComponents();
    // The test browser reports English: the texts below are the French ones.
    TestBed.inject(I18n).lang.set('fr');
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('enables one pair download only after both lenses are measured, using the latest contours', async () => {
    const createObjectURL = vi.fn((_blob: Blob) => 'blob:lens-pair');
    vi.stubGlobal(
      'URL',
      class extends URL {
        static override createObjectURL = createObjectURL;
        static override revokeObjectURL = vi.fn();
      },
    );
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      expect(this.download).toBe('contours-paire.svg');
      expect(this.href).toBe('blob:lens-pair');
    });
    const fixture = TestBed.createComponent(Home);
    const store = TestBed.inject(SessionStore);
    await fixture.whenStable();
    const button = [...(fixture.nativeElement as HTMLElement).querySelectorAll('button')].find(
      (element) => element.textContent?.includes('Télécharger la paire en SVG'),
    )!;
    expect(button.disabled).toBe(true);

    const right = ellipseContour('R', 50, 36);
    store.set('R', { contour: right });
    await fixture.whenStable();
    expect(button.disabled).toBe(true);

    const left = ellipseContour('L', 60, 40);
    store.set('L', { contour: left });
    await fixture.whenStable();
    expect(button.disabled).toBe(false);
    vi.useFakeTimers();
    button.click();
    vi.runAllTimers();
    vi.useRealTimers();
    expect(createObjectURL).toHaveBeenCalledExactlyOnceWith(expect.any(Blob));
    expect(click).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0][0];
    expect(blob.type).toBe('image/svg+xml');
    expect(await readBlob(blob)).toBe(lensPairSvg(right, left));

    const replacement = ellipseContour('R', 52, 38);
    store.set('R', { contour: replacement });
    await fixture.whenStable();
    vi.useFakeTimers();
    button.click();
    vi.runAllTimers();
    vi.useRealTimers();
    expect(createObjectURL).toHaveBeenCalledTimes(2);
    expect(await readBlob(createObjectURL.mock.calls[1][0])).toBe(lensPairSvg(replacement, left));
  });
});

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}
