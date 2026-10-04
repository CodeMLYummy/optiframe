import { Injectable, computed, effect, signal } from '@angular/core';
import { formatNumber, registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import localeFr from '@angular/common/locales/fr';

import { en } from './en';
import { es } from './es';
import { MessageKey, Messages, fr } from './fr';

/**
 * Languages of the app. To add one: copy en.ts, translate every value (the compiler lists missing keys), add it here
 * with its locale data (numbers) and its direction ('rtl' for Arabic, Hebrew, Persian...).
 */
export const LANGUAGES = [
  { code: 'fr', name: 'Français', messages: fr as Messages, dir: 'ltr' },
  { code: 'en', name: 'English', messages: en, dir: 'ltr' },
  { code: 'es', name: 'Español', messages: es, dir: 'ltr' },
] as const;

export type Lang = (typeof LANGUAGES)[number]['code'];

registerLocaleData(localeFr);
registerLocaleData(localeEs);

const STORAGE_KEY = 'optiframe.lang';
const DEFAULT_LANG: Lang = 'fr';

/** An error shown to the user: a message key, and the server's own message when there is one (always French). */
export class AppError extends Error {
  constructor(
    readonly key: MessageKey,
    readonly serverMessage?: string,
  ) {
    super(serverMessage ?? key);
  }
}

/** Current language, remembered on this device; defaults to the browser's language when the app has it. */
@Injectable({ providedIn: 'root' })
export class I18n {
  readonly lang = signal<Lang>(initialLang());
  private readonly language = computed(() => LANGUAGES.find((l) => l.code === this.lang()) ?? LANGUAGES[0]);

  constructor() {
    effect(() => {
      const l = this.language();
      document.documentElement.lang = l.code;
      document.documentElement.dir = l.dir;
      try {
        localStorage.setItem(STORAGE_KEY, l.code);
      } catch {
        // Not remembered: the choice still applies to this visit.
      }
    });
  }

  /** Message in the current language, `{name}` replaced by `params.name`. */
  readonly t = (key: MessageKey, params: Record<string, string | number> = {}): string =>
    this.language().messages[key].replace(/\{(\w+)\}/g, (m, name: string) => (name in params ? String(params[name]) : m));

  /** Number formatted for the current language (decimal comma in French and Spanish). */
  readonly num = (value: number, digits = '1.1-1'): string => formatNumber(value, this.lang(), digits);

  /** User-facing message for an error. In French the server's message is kept: it names the exact problem. */
  readonly error = (e: unknown): string => {
    if (e instanceof AppError) {
      return e.serverMessage && this.lang() === 'fr' ? e.serverMessage : this.t(e.key);
    }
    return this.t('error.unexpected');
  };
}

export function isMessageKey(key: string): key is MessageKey {
  return key in fr;
}

function initialLang(): Lang {
  const known = (code: string | null | undefined): Lang | undefined =>
    LANGUAGES.find((l) => l.code === code?.slice(0, 2).toLowerCase())?.code;
  try {
    const saved = known(localStorage.getItem(STORAGE_KEY));
    if (saved) {
      return saved;
    }
  } catch {
    // Storage blocked: fall back to the browser's language.
  }
  for (const code of navigator.languages ?? [navigator.language]) {
    const lang = known(code);
    if (lang) {
      return lang;
    }
  }
  return DEFAULT_LANG;
}
