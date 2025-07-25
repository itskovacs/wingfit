import { Routes } from '@angular/router';
import { BaseLayoutComponent } from './components/base-layout/base-layout.component';
import { AuthComponent } from './components/auth/auth.component';
import { HistoryComponent } from './components/history/history.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { PersonalRecordsComponent } from './components/personal-records/personal-records.component';
import { SettingsComponent } from './components/settings/settings.component';
import { ProgramsComponent } from './components/programs/programs.component';
import { ProgramComponent } from './components/program/program.component';
import { StatisticsComponent } from './components/statistics/statistics.component';
import { AuthGuard } from './services/auth.guard';
import { StashComponent } from './components/stash/stash.component';
import { AdminPanelComponent } from './components/admin-panel/admin-panel.component';

export const routes: Routes = [
  {
    path: 'auth',
    pathMatch: 'full',
    component: AuthComponent,
    title: 'Wingfit - Authentication',
  },

  {
    path: '',
    component: BaseLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: 'home',
        component: DashboardComponent,
        title: 'Wingfit - Planning',
      },
      {
        path: 'pr',
        component: PersonalRecordsComponent,
        title: 'Wingfit - Lightweight baby',
      },
      {
        path: 'history',
        component: HistoryComponent,
        title: 'Wingfit - History',
      },
      {
        path: 'settings',
        component: SettingsComponent,
        title: 'Wingfit - Settings',
      },
      {
        path: 'statistics',
        component: StatisticsComponent,
        title: 'Wingfit - Statistics',
      },
      {
        path: 'stash',
        component: StashComponent,
        title: 'Wingfit - Stash',
      },
      {
        path: 'adminp',
        component: AdminPanelComponent,
        title: 'Wingfit - Admin Panel',
      },

      {
        path: 'programs',
        children: [
          {
            path: '',
            component: ProgramsComponent,
            title: 'Wingfit - Programs',
          },
          {
            path: ':id',
            component: ProgramComponent,
            title: 'Wingfit - Program',
          },
        ],
      },

      { path: '**', redirectTo: '/home', pathMatch: 'full' },
    ],
  },

  { path: '**', redirectTo: '/', pathMatch: 'full' },
];
