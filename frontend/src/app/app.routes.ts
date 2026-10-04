import { Routes } from '@angular/router';

import { FacePage } from './pages/checks/face-page';
import { FitPage } from './pages/checks/fit-page';
import { FilesStep } from './pages/files-step/files-step';
import { FrameStep } from './pages/frame-step/frame-step';
import { LensStep } from './pages/lens-step/lens-step';
import { SheetStep } from './pages/sheet-step/sheet-step';
import { Steps } from './pages/steps/steps';
import { Welcome } from './pages/welcome/welcome';

export const routes: Routes = [
  { path: '', component: Welcome, title: 'OptiFrame' },
  { path: 'feuille', component: SheetStep, title: 'OptiFrame · 1' },
  { path: 'verre-droit', component: LensStep, data: { eye: 'R' }, title: 'OptiFrame · 2' },
  { path: 'verre-gauche', component: LensStep, data: { eye: 'L' }, title: 'OptiFrame · 3' },
  { path: 'monture', component: FrameStep, title: 'OptiFrame · 4' },
  { path: 'fichiers', component: FilesStep, title: 'OptiFrame · 5' },
  { path: 'verification', component: FitPage, title: 'OptiFrame · 5' },
  { path: 'essayage', component: FacePage, title: 'OptiFrame · 5' },
  { path: 'pas-a-pas', component: Steps, title: 'OptiFrame · 5' },
  { path: '**', redirectTo: '' },
];
