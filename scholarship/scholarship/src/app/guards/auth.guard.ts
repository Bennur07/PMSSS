import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { map, tap } from 'rxjs/operators';
import { AuthService } from '../auth/auth-service.service';

export const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.isLoggedIn().pipe(
    tap(isLoggedIn => {
      if (!isLoggedIn) {
        router.navigate(['/auth/signin']);
      }
    })
  );
};