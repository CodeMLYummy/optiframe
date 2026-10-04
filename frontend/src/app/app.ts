import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { I18n, LANGUAGES, Lang } from './core/i18n/i18n';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly i18n = inject(I18n);
  protected readonly languages = LANGUAGES;

  protected setLang(event: Event): void {
    this.i18n.lang.set((event.target as HTMLSelectElement).value as Lang);
  }
}
