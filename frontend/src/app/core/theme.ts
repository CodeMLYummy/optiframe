import { Injectable, computed, effect, signal } from '@angular/core';

export type ThemeChoice = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'optiframe.theme';
const ORDER: ThemeChoice[] = ['system', 'light', 'dark'];

/** Light or dark: follows the system unless the user picked one, remembered on this device. */
@Injectable({ providedIn: 'root' })
export class Theme {
  readonly choice = signal<ThemeChoice>(load());
  private readonly media = window.matchMedia?.('(prefers-color-scheme: dark)');
  private readonly systemDark = signal(this.media?.matches ?? false);
  readonly dark = computed(() =>
    this.choice() === 'system' ? this.systemDark() : this.choice() === 'dark',
  );

  constructor() {
    this.media?.addEventListener('change', (e) => this.systemDark.set(e.matches));
    effect(() => {
      const choice = this.choice();
      const root = document.documentElement;
      if (choice === 'system') {
        root.removeAttribute('data-theme');
      } else {
        root.dataset['theme'] = choice;
      }
      try {
        localStorage.setItem(STORAGE_KEY, choice);
      } catch {
        // Not remembered: the choice still applies to this visit.
      }
    });
    effect(() => {
      // Browser chrome (address bar on Android) follows the wall colour.
      const color = getComputedStyle(document.documentElement).getPropertyValue('--wall').trim();
      this.dark();
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', color);
    });
  }

  cycle(): void {
    this.choice.update((c) => ORDER[(ORDER.indexOf(c) + 1) % ORDER.length]);
  }
}

function load(): ThemeChoice {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark' || v === 'system') {
      return v;
    }
  } catch {
    // Storage blocked: follow the system.
  }
  return 'system';
}
