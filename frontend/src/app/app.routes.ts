import { Routes } from '@angular/router';

import { Home } from './pages/home/home';
import { Steps } from './pages/steps/steps';

export const routes: Routes = [
  { path: '', component: Home, title: 'OptiFrame' },
  { path: 'pas-a-pas', component: Steps, title: 'OptiFrame · Pas à pas' },
  { path: '**', redirectTo: '' },
];
