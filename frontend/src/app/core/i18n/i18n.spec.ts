import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { en } from './en';
import { es } from './es';
import { fr } from './fr';
import { AppError, I18n } from './i18n';

describe('I18n', () => {
  it('translates with parameters and switches language', () => {
    const i18n = TestBed.inject(I18n);
    i18n.lang.set('fr');
    expect(i18n.t('frame.standardBridge', { mm: 18 })).toBe('Sans PD : pont standard de 18 mm.');
    i18n.lang.set('en');
    expect(i18n.t('frame.standardBridge', { mm: 18 })).toBe('No PD: standard 18 mm bridge.');
  });

  it('formats numbers for the language', () => {
    const i18n = TestBed.inject(I18n);
    i18n.lang.set('fr');
    expect(i18n.num(31.25, '1.1-1')).toBe('31,3');
    i18n.lang.set('en');
    expect(i18n.num(31.25, '1.1-1')).toBe('31.3');
  });

  it("keeps the server's detailed message in French, translates the code otherwise", () => {
    const i18n = TestBed.inject(I18n);
    const e = new AppError('error.PHOTO_BLURRY', 'Photo floue (détail du serveur).');
    i18n.lang.set('fr');
    expect(i18n.error(e)).toBe('Photo floue (détail du serveur).');
    i18n.lang.set('es');
    expect(i18n.error(e)).toBe(es['error.PHOTO_BLURRY']);
  });

  it('uses the same parameters in every language', () => {
    const params = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const messages of [en, es]) {
      for (const [key, text] of Object.entries(fr)) {
        expect(params(messages[key as keyof typeof fr]), key).toEqual(params(text));
      }
    }
  });
});
