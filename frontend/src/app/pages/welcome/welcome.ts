import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Flow } from '../../core/flow';
import { I18n } from '../../core/i18n/i18n';
import { Icon } from '../../ui/icon';

/** First screen: the whole procedure shown as an acuity chart, read from the top line. */
@Component({
  selector: 'app-welcome',
  imports: [RouterLink, Icon],
  template: `
    <h2 class="title">{{ i18n.t('welcome.title') }}</h2>

    <ol class="chart" [attr.aria-label]="i18n.t('welcome.chart')">
      @for (s of flow.steps; track s.path; let i = $index) {
        <li [class.read]="flow.started() && i < flow.firstOpen()" [class.current]="i === start()">
          <span class="n num" aria-hidden="true">{{ i + 1 }}</span>
          <span class="name">{{ i18n.t(s.label) }}</span>
          @if (flow.started() && i < flow.firstOpen()) {
            <app-icon name="check" class="ok" />
          }
        </li>
      }
    </ol>

    <section class="need">
      <h3>{{ i18n.t('welcome.need') }}</h3>
      <ul>
        <li><app-icon name="printer" />{{ i18n.t('welcome.needSheet') }}</li>
        <li><app-icon name="sun" />{{ i18n.t('welcome.needLight') }}</li>
        <li><app-icon name="glasses" />{{ i18n.t('welcome.needLenses') }}</li>
      </ul>
    </section>

    <div class="cta">
      <a class="btn primary block" [routerLink]="['/', flow.steps[start()].path]">
        {{ i18n.t(flow.started() ? 'nav.resume' : 'nav.start') }}
        <app-icon name="arrow-right" />
      </a>
    </div>
  `,
  styles: `
    :host {
      display: flex;
      flex: 1;
      flex-direction: column;
    }
    .title {
      max-width: 22ch;
      font-size: 1.2rem;
      font-weight: 600;
      line-height: 1.3;
      color: var(--ink-2);
      text-wrap: balance;
    }
    .chart {
      display: grid;
      gap: 6px;
      margin: 28px 0 32px;
      padding: 8px 0 4px;
    }
    .chart li {
      position: relative;
      display: grid;
      grid-template-columns: 2rem 1fr 2rem;
      align-items: baseline;
      padding: 8px 0 10px;
      text-align: center;
    }
    .chart .n {
      color: var(--ink-3);
      font-size: 0.85rem;
      font-weight: 600;
      text-align: start;
    }
    .chart .name {
      font-stretch: 125%;
      font-weight: 750;
      line-height: 1;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      overflow-wrap: anywhere;
    }
    .chart li:nth-child(1) .name {
      font-size: clamp(2rem, 1.2rem + 4vw, 2.7rem);
    }
    .chart li:nth-child(2) .name {
      font-size: clamp(1.5rem, 1rem + 2.6vw, 2rem);
    }
    .chart li:nth-child(3) .name {
      font-size: clamp(1.28rem, 0.9rem + 2vw, 1.62rem);
    }
    .chart li:nth-child(4) .name {
      font-size: clamp(1.08rem, 0.85rem + 1.2vw, 1.3rem);
    }
    .chart li:nth-child(5) .name {
      font-size: clamp(0.92rem, 0.8rem + 0.6vw, 1.05rem);
    }
    .chart .read .name {
      color: var(--ink-3);
    }
    .chart app-icon {
      --icon-size: 18px;
      justify-self: end;
      align-self: center;
    }
    .chart .current::after {
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 3px;
      background: var(--red);
    }
    .need {
      display: grid;
      gap: 12px;
      padding-top: 20px;
      border-top: 1px solid var(--rule);
    }
    h3 {
      font-size: 0.95rem;
      font-weight: 650;
    }
    .need ul {
      display: grid;
      gap: 10px;
    }
    .need li {
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--ink-2);
      --icon-size: 20px;
    }
    .need app-icon {
      color: var(--ink);
    }
    .cta {
      position: sticky;
      bottom: 0;
      margin: auto -18px 0;
      padding: 24px 18px calc(16px + env(safe-area-inset-bottom));
      background: linear-gradient(transparent, var(--panel) 24px);
    }
    @media (min-width: 960px) {
      .cta {
        margin: 32px 0 0;
        padding: 0 0 40px;
        background: none;
      }
    }
  `,
})
export class Welcome {
  protected readonly i18n = inject(I18n);
  protected readonly flow = inject(Flow);
  protected readonly start = () => (this.flow.started() ? this.flow.firstOpen() : 0);
}
