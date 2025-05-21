import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { adminGuard } from './guards/admin.guard';

export const routes: Routes = [
 { path: '', redirectTo: '/home', pathMatch: 'full' },
  {
    path: 'auth',
    children: [
      { 
        path: 'signin', 
        loadComponent: () => import('./signin/signin.component').then(c => c.SigninComponent) 
      },
      { 
        path: 'signup', 
        loadComponent: () => import('./signup/signup.component').then(c => c.SignupComponent) 
      }
    ]
  },
  { 
    path: 'home', 
    loadComponent: () => import('./home/home.component').then(c => c.HomeComponent),
    canActivate: [authGuard],
    
  },
  {
    path: 'apply/:id',
    loadComponent: () => import('./scholarship-application/scholarship-application.component').then(c => c.ScholarshipApplicationComponent),
    canActivate: [authGuard]
  },
  { 
    path: 'admin', 
    loadComponent: () => import('./admin-dashboard/admin-dashboard.component').then(c => c.AdminDashboardComponent),
    canActivate: [adminGuard]
  },
  { 
    path: 'live-status', 
    loadComponent: () => import('./live-status/live-status.component').then(c => c.LiveStatusComponent),
    canActivate: [authGuard] 
  },
  { path: '**', redirectTo: '/auth/signin' }
];