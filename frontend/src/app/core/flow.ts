import { Injectable, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter, map } from 'rxjs';

import { MessageKey } from './i18n/fr';
import { SessionStore } from './session.store';
import { SheetSettings } from './sheet-settings';

export interface FlowStep {
  path: string;
  label: MessageKey;
  /** Shown beside a disabled Continue: what is missing before the next step. */
  blocker: MessageKey | null;
}

export const STEPS: readonly FlowStep[] = [
  { path: 'feuille', label: 'step.sheet', blocker: 'block.sheet' },
  { path: 'verre-droit', label: 'step.right', blocker: 'block.right' },
  { path: 'verre-gauche', label: 'step.left', blocker: 'block.left' },
  { path: 'monture', label: 'step.frame', blocker: 'block.frame' },
  { path: 'fichiers', label: 'step.files', blocker: null },
];

/** Optional checks reached from the Files step; they return there. */
export const SIDE_PATHS = ['verification', 'essayage', 'pas-a-pas'];

/** Where the user is in the guided path, and whether each step's result exists. */
@Injectable({ providedIn: 'root' })
export class Flow {
  private readonly router = inject(Router);
  private readonly store = inject(SessionStore);
  private readonly sheet = inject(SheetSettings);

  readonly steps = STEPS;
  private readonly path = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects.replace(/^\/|[?#].*$/g, '')),
    ),
    { initialValue: '' },
  );
  readonly index = computed(() => STEPS.findIndex((s) => s.path === this.path()));
  readonly side = computed(() => SIDE_PATHS.includes(this.path()));

  /** Result of each step: the next one can start once it is there. */
  readonly done = computed(() => [
    this.sheet.scale() !== null,
    !!this.store.lenses().R,
    !!this.store.lenses().L,
    !!this.store.frame(),
    true,
  ]);

  /** First step whose result is missing, where Resume leads; the last step once everything is done. */
  readonly firstOpen = computed(() => {
    const i = this.done().indexOf(false);
    return i < 0 ? STEPS.length - 1 : i;
  });
  readonly started = computed(
    () => Object.keys(this.store.lenses()).length > 0 || !!this.store.frame(),
  );

  go(index: number): void {
    void this.router.navigate(['/', STEPS[index].path]);
  }
}
