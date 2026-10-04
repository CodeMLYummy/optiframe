import { Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';

import { Flow } from './core/flow';
import { FrameDesign } from './core/frame-design';
import { I18n, LANGUAGES, Lang } from './core/i18n/i18n';
import { SessionStore } from './core/session.store';
import { Theme, ThemeChoice } from './core/theme';
import { MessageKey } from './core/i18n/fr';
import { Icon, IconName } from './ui/icon';

const THEME_ICONS: Record<ThemeChoice, IconName> = {
  system: 'sun-moon',
  light: 'sun',
  dark: 'moon',
};
const THEME_LABELS: Record<ThemeChoice, MessageKey> = {
  system: 'app.themeSystem',
  light: 'app.themeLight',
  dark: 'app.themeDark',
};

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, Icon],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly i18n = inject(I18n);
  protected readonly theme = inject(Theme);
  protected readonly flow = inject(Flow);
  protected readonly design = inject(FrameDesign);
  protected readonly store = inject(SessionStore);
  private readonly router = inject(Router);
  protected readonly languages = LANGUAGES;

  /** Side pages belong to the Files step. */
  protected readonly current = computed(() =>
    this.flow.side() ? this.flow.steps.length - 1 : this.flow.index(),
  );

  /** On the Frame step, before a frame exists, the main action generates it. */
  protected readonly generateHere = computed(
    () => this.flow.index() === 3 && !this.store.frame() && this.store.bothMeasured(),
  );

  protected readonly blocker = computed(() => {
    const i = this.flow.index();
    if (i < 0 || this.flow.done()[i] || this.generateHere()) {
      return null;
    }
    return this.flow.steps[i].blocker;
  });

  protected readonly themeIcon = computed<IconName>(() => THEME_ICONS[this.theme.choice()]);

  protected readonly themeLabel = computed(() => this.i18n.t(THEME_LABELS[this.theme.choice()]));

  protected stepLabel(i: number): string {
    return this.i18n.t('nav.step', {
      n: i + 1,
      total: this.flow.steps.length,
      name: this.i18n.t(this.flow.steps[i].label),
    });
  }

  protected setLang(event: Event): void {
    this.i18n.lang.set((event.target as HTMLSelectElement).value as Lang);
  }

  protected next(): void {
    this.flow.go(this.flow.index() + 1);
  }

  protected back(): void {
    const i = this.flow.index();
    if (i <= 0) {
      void this.router.navigate(['/']);
    } else {
      this.flow.go(i - 1);
    }
  }
}
